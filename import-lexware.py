import os
import sys
import getpass
import datetime
import collections
from contextlib import ExitStack

import sqlalchemy as sa

from kneipy_core import database
from kneipy_core.lib.sqlalchemy_session_scope import \
    session_scope
from kneipy_core.lib.timed import timed

VERBOSE = False
LEXWARE_FIELD_MAPPING = {
    'lexware_transaction_nr': 'Buchungsnummer',
    'bookingtime': 'Buchungsdatum',
    'receiptdate': 'Belegdatum',
    'receipt': 'Belegnummer',
    'text': 'Buchungstext',
    'amount': 'Buchungsbetrag',
    'credit': 'Sollkonto',
    'debit': 'Habenkonto',
}

LEXWARE_ACCOUNT_MAPPING = {
    'nr': 'Konto-Nummer',
    'name': 'Kontenbezeichnung',
    'category': 'Kontenkategorie',
    'z_aktiva': 'Zuordnung Aktiva',
    'z_passiva': 'Zuordnung Passiva',
    'z_guv': 'Zuordnung GuV'
}
LexwareAccountLine = collections.namedtuple(
    'LexwareAccountLine', LEXWARE_ACCOUNT_MAPPING.keys()
)

LEXWARE_ACCOUNT_BALANCE_MAPPING = {
    'A-1. Forderungen aus Lieferungen und Leistungen':
        database.AccountTypes.FromSales,
    'P-3. Verbindlichkeiten aus Lieferungen u. Leistungen':
        database.AccountTypes.FromSales,
    'A-2. Forderungen gegen verbundene Unternehmen':
        database.AccountTypes.ConnectedEntities,
    'P-5. Verbindlichkeiten gegenüber verbundenen Unternehmen':
        database.AccountTypes.ConnectedEntities,
    'A-4. sonstige Vermögensgegenstände':
        database.AccountTypes.Others,
    'P-7. sonstige Verbindlichkeiten':
        database.AccountTypes.Others,
    'A-IV. Kassenbestand. Guthaben b. Kreditinstituten. Postgiro':
        database.AccountTypes.Financial,
    'P-1. Verbindlichkeiten gegenüber Kreditinstituten':
        database.AccountTypes.Financial,
    'P-I. Kapital':
        database.AccountTypes.Capital,
    'P-IV. Gewinn- und Verlustvortrag':
        database.AccountTypes.PreviousResults,
    'GuV-Materialaufwand':
        database.AccountTypes.Expenses,
    'GuV-Personalaufwand':
        database.AccountTypes.Expenses,
    'GuV-Umsatzerlöse':
        database.AccountTypes.Profits,
    'GuV-Abschreibungen':
        database.AccountTypes.Depreciation,
    'P-4. Verb. aus Annahme gez. Wechsel und Ausstellung eig. Wechsel':
        database.AccountTypes.Transit,
}


LexwareJournalLine = collections.namedtuple(
    'LexwareJournalLine', LEXWARE_FIELD_MAPPING.keys()
)


class LexwareImporter():
    def __init__(self, name, company):
        self.session = database.Session()
        self.balancesheet = database.BalanceSheet(
            name=name,
            company=company
        )
        self.session.add(self.balancesheet)
        self.session.flush()
        self.accounts = {}
        self.cancel_transactions = {
            'ok': 0,
            'multiple_same': 0,
            'multiple_single': 0,
            'notfound': 0,
            'amount_positive': 0
        }

    def decode_with_cleanup(self, line):
        """
        Encoding Chaos aufräumen und möglichst viele kaputte Umlaute reparieren
        """
        l = line.decode("cp1252") \
            .replace("\r\n", "").replace("\x80", "€")\
            .replace("\x84", "ä").replace("\x81", "ü") \
            .replace("\x94", "ö")
        broken_enc_chars = [
            "Ã€",  # ä
            "Ã",   # ß
            "Ã¶",  # ö
            "ÃŒ",  # ü
            "Ã¤",  # ä
        ]
        if any(c in l for c in broken_enc_chars):
            l = l.encode("cp1252").decode("utf-8", "ignore")
        return l.replace("ÃƒÂ¤", "ä").replace("Ã¼", "ü") \
            .replace("ÃƒÂ¼", "ü").replace("ÃŸ", "ß")

    def get_account(self, lexware_account_id):
        if lexware_account_id not in self.accounts and \
                lexware_account_id > 11000:
            # Personenkonto automatisch anlegen
            self.accounts[lexware_account_id] = database.Account(
                external_refs={
                    'lexware': str(lexware_account_id)
                },
                balancesheet_id=self.balancesheet.id,
                type=database.AccountTypes.Person
            )
            self.session.add(self.accounts[lexware_account_id])
            self.session.flush()
        return self.accounts[lexware_account_id].id

    def import_journal(self, lexware_journal):
        lines = lexware_journal.splitlines()

        with timed('import {} lines to {}'.format(
                len(lines),
                self.balancesheet.name)):
            start_line = lines[0]
            data_lines = lines[1:]
            fields = start_line.decode('cp1252').strip().split('\t')

            for lexware_field in LEXWARE_FIELD_MAPPING.values():
                if lexware_field not in fields:
                    raise ValueError(
                        'erforderliches Feld {} is nicht in Journal enthalten'
                        .format(lexware_field)
                    )

            field_mapping_idx = dict(
                (field, fields.index(lexware_field))
                for field, lexware_field in LEXWARE_FIELD_MAPPING.items()
            )

            with ExitStack() as tg_stack:
                self.last_transaction_nr = -1
                self.splitbuchung_start = {}
                self.transaction_group = None

                for l in data_lines:
                    l_parts = self.decode_with_cleanup(l).split('\t')
                    parsed_line = LexwareJournalLine(
                        **dict(
                            (field, l_parts[idx])
                            for field, idx in field_mapping_idx.items()
                        )
                    )
                    self.import_journal_line(parsed_line, tg_stack)
                    self.last_transaction_nr = \
                        int(parsed_line.lexware_transaction_nr)
        print('Stornos:', self.cancel_transactions)
        print('')

    def new_transaction_group(self, line, tg_stack):
        tg_stack.close()  # letzte Gruppe schließen
        self.transaction_group = tg_stack.enter_context(
            self.balancesheet.transact_core(
                receipt=line.receipt,
                receiptdate=datetime.datetime.strptime(
                    line.receiptdate,
                    "%d.%m.%y"
                ).date(),
                text=line.text
            )
        )
        if VERBOSE:
            print('===== TG')

    def transaction(self, line, credit=None, debit=None,
                    force_not_cancelled=False):
        credit = int(line.credit if credit is None else credit)
        debit = int(line.debit if debit is None else debit)
        amount = int(100*float(
            line.amount.replace(".", "").replace(",", ".")
        ))
        if line.text.startswith('<Storno> ') and not force_not_cancelled:
            # finden der stornierten Buchung
            original_transactions = self.session.query(database.Transaction) \
                .filter_by(
                    balancesheet_id=self.balancesheet.id,
                    text=line.text[len('<Storno> '):],
                    credit_account_id=self.get_account(credit),
                    debit_account_id=self.get_account(debit),
                    product_id=database.Product.EURO_CT_ID,
                    amount=-amount
                ).options(
                    sa.orm.joinedload('cancelled_by')
                ).all()
            original_transaction = None
            if len(original_transactions) == 0:
                self.cancel_transactions['notfound'] += 1
            elif len(original_transactions) == 1:
                original_transaction = original_transactions[0]
            elif len(original_transactions) > 1:
                for t in original_transactions:
                    if t.cancelled_by is None:
                        if original_transaction is not None:
                            self.cancel_transactions['multiple_single'] += 1
                        original_transaction = original_transactions[0]

            if original_transaction is None:
                self.cancel_transactions['notfound'] += 1
            elif original_transaction.cancelled_by is not None:
                self.cancel_transactions['multiple_same'] += 1
            elif amount > 0:
                self.cancel_transactions['amount_positive'] += 1

            if original_transaction is None or \
                    original_transaction.cancelled_by is not None or \
                    amount > 0:
                return self.transaction(
                    line=line, credit=credit, debit=debit,
                    force_not_cancelled=True
                )
            else:
                if VERBOSE:
                    print(
                        "storno", line.lexware_transaction_nr,
                        line.text, original_transaction.id
                    )
                # Buchung stornieren
                self.cancel_transactions['ok'] += 1
                self.transaction_group.cancel_transaction(
                    transaction_id=original_transaction.id,
                    credit_account_id=self.get_account(credit),
                    debit_account_id=self.get_account(debit),
                    product_id=database.Product.EURO_CT_ID,
                    original_amount=-amount,
                    text=line.text,
                )
        else:
            if VERBOSE:
                print("normal", line.lexware_transaction_nr, line.text)
            if amount < 0:
                # komischer Kram => Konten tauschen
                credit, debit = debit, credit
                amount = -amount
                if VERBOSE:
                    print("flip")
            self.transaction_group.transaction(
                credit_account_id=self.get_account(credit),
                debit_account_id=self.get_account(debit),
                product_id=database.Product.EURO_CT_ID,
                amount=amount,
                text=line.text
            )

    def import_journal_line(self, line, tg_stack):
        if line.credit in ["0", ""] or line.debit in ["0", ""]:
            # Splitbuchung
            if int(line.lexware_transaction_nr) != self.last_transaction_nr:
                # Start der Splitbuchung
                self.new_transaction_group(line, tg_stack)

                self.splitbuchung_start = {
                    'credit': line.credit, 'debit': line.debit
                }
                return
            else:
                # weitere Teile der Splitbuchung
                credit, debit = line.credit, line.debit
                if not credit:
                    credit = self.splitbuchung_start["credit"]
                    assert credit != ""
                if not debit:
                    debit = self.splitbuchung_start["debit"]
                    assert debit != ""
                self.transaction(line, credit, debit)

        else:
            # normale Buchung
            self.new_transaction_group(line, tg_stack)
            self.transaction(line)

    def import_accounts(self, lexware_accounts, guv_parent):
        lines = lexware_accounts.splitlines()
        start_line = lines[0]
        data_lines = lines[1:]
        fields = start_line.decode('cp1252').strip().split('\t')

        for lexware_field in LEXWARE_ACCOUNT_MAPPING.values():
            if lexware_field not in fields:
                raise ValueError(
                    'erforderliches Feld {} ist nicht in Kontenplan enthalten'
                    .format(lexware_field)
                )

        field_mapping_idx = dict(
            (field, fields.index(lexware_field))
            for field, lexware_field in LEXWARE_ACCOUNT_MAPPING.items()
        )

        for l in data_lines:
            l_parts = self.decode_with_cleanup(l).split('\t')
            parsed_line = LexwareAccountLine(**dict(
                (field, l_parts[idx])
                for field, idx in field_mapping_idx.items()
            ))
            account_type = None
            key_akt = 'A-' + parsed_line.z_aktiva
            key_pas = 'P-' + parsed_line.z_passiva
            key_guv = 'GuV-' + parsed_line.z_guv
            if key_akt in LEXWARE_ACCOUNT_BALANCE_MAPPING:
                account_type = LEXWARE_ACCOUNT_BALANCE_MAPPING[key_akt]
            elif key_pas in LEXWARE_ACCOUNT_BALANCE_MAPPING:
                account_type = LEXWARE_ACCOUNT_BALANCE_MAPPING[key_pas]
            elif key_guv in LEXWARE_ACCOUNT_BALANCE_MAPPING:
                account_type = LEXWARE_ACCOUNT_BALANCE_MAPPING[key_guv]
            elif parsed_line.category == 'Saldovortrag':
                account_type = database.AccountTypes.BalanceSheetOpening
            elif parsed_line.category == 'Betriebsausgaben':
                account_type = database.AccountTypes.Expenses
            else:
                continue

            if parsed_line.nr in ['04031', '06330', '06350', '06001', '05001', '05051', '05101']:
                parsed_line = parsed_line._replace(name=parsed_line.name + ' ' + parsed_line.nr)

            self.accounts[int(parsed_line.nr)] = database.Account(
                external_refs={
                    'lexware': str(parsed_line.nr)
                },
                balancesheet_id=self.balancesheet.id,
                name=parsed_line.name,
                type=account_type
            )
        for a in self.accounts.values():
            if a.type == database.AccountTypes.Expenses:
                a.parent = self.accounts[guv_parent]
            if a.type == database.AccountTypes.Profits:
                a.parent = self.accounts[guv_parent]
        for a in self.accounts.values():
            self.session.add(a)
        self.session.flush()


if __name__ == "__main__":
    database_uri = os.environ.get(
        'DATABASE_URI',
        'postgresql://{}@localhost/kneipy-dev'.format(
            getpass.getuser()

        )
    )
    database.connect(database_uri, echo=False)
    assert database.engine.connect()
    with session_scope(database.Session()) as s:
        # seed database with essential data
        s.execute(database.Product.insert_euro_cents())
    company = database.Company(name='AV Buchhaltung')
    for fn in sorted(os.listdir(sys.argv[1])):
        if not fn.startswith('jour'):
            continue
        print('===', fn)
        importer = LexwareImporter(fn, company)
        importer.import_accounts(
            open(
                os.path.join(sys.argv[1], 'KTPL_BP.txt'),
                'rb'
            ).read(),
            3400
        )
        importer.import_journal(
            open(
                os.path.join(sys.argv[1], fn),
                'rb'
            ).read()
        )
        importer.session.commit()
