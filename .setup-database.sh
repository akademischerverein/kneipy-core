#!/bin/bash

psql postgres <<EOF
    DROP DATABASE IF EXISTS "kneipy-dev";
    DROP DATABASE IF EXISTS "kneipy-tests";
    DROP ROLE IF EXISTS "kneipy-dev";
    CREATE ROLE "kneipy-dev"
        PASSWORD 'kneipy-dev'
        NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT LOGIN;
    CREATE DATABASE "kneipy-dev" OWNER "kneipy-dev";
    CREATE DATABASE "kneipy-tests" OWNER "kneipy-dev";

    \c kneipy-dev
    CREATE EXTENSION pgcrypto;
    \c kneipy-tests
    CREATE EXTENSION pgcrypto;
EOF
