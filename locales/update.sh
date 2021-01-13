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

    msgfmt "$file.mo" --output-file "$file.po"; done

