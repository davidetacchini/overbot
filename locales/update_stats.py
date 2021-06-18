import os
import re
import json

LOCALE_DIR = os.getcwd()
LOCALE = re.compile("^[a-z]{2}_[A-Z]{2}$")
locales = filter(lambda d: LOCALE.match(d), os.listdir(LOCALE_DIR))


def main():
    results = {}

    for locale in locales:
        with open(f"{locale}/LC_MESSAGES/main.po") as fp:
            file = fp.readlines()

        lookup = {k: v for k, v in enumerate(file)}

        total = -1  # remove first occurence
        empty = 0
        for index, line in enumerate(file):
            if line.startswith("msgstr"):
                total += 1
            if line == 'msgstr ""\n':
                if lookup.get(index + 1, "\n") == "\n":
                    empty += 1

        percentage = str(round(100 - ((100 * empty) / total), 2))
        results[locale] = percentage

    with open("stats.json", "w") as fp:
        json.dump(results, fp, sort_keys=True, indent=4)


if __name__ == "__main__":
    main()
