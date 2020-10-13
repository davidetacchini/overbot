#!/bin/bash
if [ -z "$1" ]
  then
    echo "Please provide a database name."
    exit 1
fi

echo "Removing old schema..."
rm schema.sql
touch schema.sql
echo "Dumping database $1..."
pg_dump -U postgres $1 --schema-only > schema.sql