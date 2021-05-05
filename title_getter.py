"""
Script très spécifique au site de test, permet depuis une page statique de capter les noms des livres.
(fast and dirty, sert surtout pour obtenir une liste de livres à extraire facilement, afin de tester la librairie)
"""

import re


if __name__ == '__main__':
    with open("file.html", "r", encoding="utf-8") as file:
        text_file = file.read()
        titles = re.findall("<div style=\"margin: 0px; padding: 0px; border: 0px;\">(.+)<em>[\s\S]+?</em>[\s\S]?</div>", text_file)


    with open("web.txt", "a", encoding="utf-8") as file:
        print(titles)
        for title in titles:
            file.writelines(title + "\n")
