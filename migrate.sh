#!/bin/sh

DATABASE=$1

if [ -z "$DATABASE" ]; then
    echo I need a database
    exit 1
fi

VERSIONS=$(eval echo bin/start_openupgrade*)
for version in $VERSIONS; do
    $version --update=all --stop-after-init --database=$DATABASE
done
