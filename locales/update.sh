#!/bin/bash

xgettext \
    --files-from POTFILES.in \
    --from-code utf-8 \
    --directory ../ \
    --output main.pot

for locale in */; do
    file="$locale/LC_MESSAGES/main"

    msgmerge \
        --update \
        --no-fuzzy-matching \
        --backup off \
        "$file.po" \
        main.pot

    msgfmt "$file.po" --output-file "$file.mo"; done

python3 update_stats.py
