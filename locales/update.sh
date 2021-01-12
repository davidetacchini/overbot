#!/bin/bash

xgettext \
    --files-from POTFILES.in \
    --from-code utf-8 \
    --directory ../ \
    --output main.pot

for locale in */; do
    printf "$locale\n"; done
    file="$locale/LC_MESSAGES/main"

    msgmerge \
        --update \
        --no-fuzzy-matching \
        --backup off \
        "$file.po" \
        main.pot

    # msgfmt "$file.mo" --output-fil-output-file "$file.po"; done

