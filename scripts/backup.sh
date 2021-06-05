#!/bin/bash
if [ -z "$1" ]; then
    echo "Please provide a database name."
    exit 1
fi

echo "Backing up database $1..."
pg_dump -h localhost -U davide -d $1 > backup.sql
echo "$1 has been successfully backed up!"
