def main():
    locales = ("it_IT", "en_US", "ru_RU", "ko_KR", "ja_JP", "de_DE", "fr_FR")
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

    with open("stats.txt", "w") as fp:
        for key, value in results.items():
            to_write = key + ": " + value + "%" + "\n"
            fp.write(to_write)


if __name__ == "__main__":
    main()
