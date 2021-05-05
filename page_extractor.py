"""
Premier jet d'un extracteur de données html via selenium. 

La librairie permet d'extraire des livres/contenus présentés sous forme de pagination.
La version actuelle est spécifique à un site de test.

Les livres sont extraits selon leur titre. Le contenu est placé en chapitres (dossiers) 
et sous-chapitres (fichiers de contenu) dans un dossier nommant le livre.
Les caractères spéciaux sont remplacés ou extraits (windows friendly) pour les noms de dossier.
Les images sont extraites et placées dans un dossier unique.
Le contenu du livre et son ordonnancement est persité dans un manifeste "summary.json".

"""

from os import path, mkdir, curdir, rename, remove, rmdir
from shutil import  rmtree
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import urllib.request
import re
import json


class BookContext:
    """
    contient les données du livre en cours d'extraction.
    
    """
    localdir = None
    chapters_names = []
    current_chapter_title = ""
    current_page_file_path = ""
    previous_page_url = ""
    current_page_id = None
    current_sub_chapter_id = 0

    def __init__(self, name):
        self.name = name
        self._initialize_dirs()
        self.chapters_dir = path.join(self.localdir, "chapters")
        self.images_dir = path.join(self.localdir, "images")
        self.chapters_names = []
        self.sub_chapters_names = {}

    def _initialize_dirs(self):
        mkdir(self.name)
        mkdir(path.join(self.name, "chapters"))
        mkdir(path.join(self.name, "images"))
        self.localdir = self.name


class PageMaker:
    """
    Permet les étapes de construction des pages du livre.
    - création
    
    """

    def __init__(self, book_context):
        assert isinstance(book_context, BookContext)
        self.context = book_context
        self.book_path = book_context.chapters_dir

    def initialize_new_chapter(self, chapter_name):
        mkdir(self.book_path, chapter_name)
        print("creation du chapitre {}".format(chapter_name))

    def create_new_chapter(self):
        self.context.current_chapter_title =re.sub(r'([|:?\\\/<>*^])', '', self.context.current_chapter_title)
        mkdir(path.join(self.context.chapters_dir, self.context.current_chapter_title))

    def save_current_sub_chapter(self, content):
        with open(path.join(self.context.current_page_file_path), 'w', encoding="utf-8") as page:
            page.write(content)
            print("injection du contenu")

    def generate_json_summary(self):
    """
    Génère le manifest du livre.
    
    """
        with open(path.join(self.context.localdir, 'summary.json'), 'w', encoding='utf-8') as summary:
            data = {
                "chapters": self.context.chapters_names,
                "sub_chapters": self.context.sub_chapters_names
            }
            json.dump(data, summary)

    def _format_images_src_properties(self, page_path):
        print("fichier %s" % page_path)
        tmp_path_page = page_path + ".tmp"
        # fichier original renommé
        rename(page_path, tmp_path_page)
        # création du fichier formatté
        with open(tmp_path_page, "r", encoding="utf-8") as book:
            lines = list(book.readlines())
            with open(page_path, "a", encoding="utf-8") as newbook:
                for line in lines:
                    if "src" in line:
                        try:
                            src = re.findall('"([^"]*)"', line.split("src")[1])[0]
                            alt = re.findall('"([^"]*)"', line.split("alt")[1])[0]
                            new_src = alt
                            if alt != "":
                                new_src = "[%{}%]".format(alt.split("/")[-1])
                                print("indexage de {} dans {}".format(new_src, page_path))
                            newline = line.replace(src, new_src)
                            newbook.write(newline)
                        except IndexError:
                            print("chargement source impossible :\n'{}'".format(line))
                    else:
                        newbook.write(line)
        remove(tmp_path_page)

    def reformat_images_src(self):
        print("------ Indexage des images -------")
        for chapter in self.context.sub_chapters_names.keys():
            chapter = re.sub(r'([|:?\\\/<>*^])', '', chapter)
            for sub_chapters in self.context.sub_chapters_names[chapter]:
                sub_chapters = re.sub(r'([|:?\\\/<>*^])', '', sub_chapters)
                self._format_images_src_properties(path.join(self.context.chapters_dir, chapter, sub_chapters))


class PageExtractor:
    """
    classe principale,
    permet l'extaction complète du livre.
    Nécessiste l'ajout du chromedriver dans le dossier courant.
    
    """
    url = "dummy/url"
    login = "user"
    pwd = "password"
    driver_path = "chromedriver.exe"
    __driver = None

    def __init__(self, bookname, hidden_mode=False):
        self.hidden_mode = hidden_mode
        self.context = BookContext(bookname)
        self.page_maker = PageMaker(self.context)

    @property
    def driver(self):
        if not self.__driver:
            options = Options()
            options.add_argument('--headless')
            if self.hidden_mode:
                self._driver = webdriver.Chrome(self.driver_path, options=options)
            else:
                self._driver = webdriver.Chrome(self.driver_path)
            print("connection à Chrome")
            self._connect_to_site()

        return self._driver

    def _connect_to_site(self):
        self.driver.get(self.url)
        print("ouverture de l'url")
        self.driver.find_element_by_name("Login").send_keys(self.login + Keys.ENTER)
        self.driver.implicitly_wait(1)
        self.driver.find_element_by_name("Password").send_keys(self.pwd + Keys.ENTER)
        print("insertion/validation des identifiants")
        self.driver.implicitly_wait(10)

    def _go_to_first_book_page(self):
        self.driver.find_element_by_xpath("//input[@class='form-control w-auto']").send_keys(self.context.name + Keys.ENTER)
        print("recherche du livre")
        results = self.driver.find_elements_by_class_name("div-resource")
        print("selection du premier choix")
        results[0].click()
        print("----------- ouverture livre ------------")

    def get_description_book_page(self):
        self.context.current_page_file_path = path.join(self.context.chapters_dir, "description.html")
        description = self.driver.find_element_by_class_name("Left").get_attribute("innerHTML")
        self.page_maker.save_current_sub_chapter(description)
        print("injection description")

    def get_subtitle(self, content):
        # captation du contenu du h1, donc du titre
        val = re.findall(r'<h1 class="title">([\s\S]+)</h1>', content)[0]
        # retrait des rollbacks
        val = val.replace('\n', '')
        # retrait des balises dans le titre (strong, b, etc)
        val = re.sub('(<[\s\S]+>)', '', val)
        self.context.sub_chapters_names[self.context.current_chapter_title].append(val)
        # retrait des caractères non autorisés dans un nom de fichier (windows friendly)
        val = re.sub(r'([|:?\\\/<>*^])', '', val)
        return val

    def get_page(self):
        self.context.previous_page_url = self.driver.current_url
        self.context.current_page_id = self.context.previous_page_url.split("=")[-1]
        content = self.driver.find_element_by_class_name("sect1").get_attribute("innerHTML")
        subtitle = self.get_subtitle(content)
        self.context.current_page_file_path = path.join(self.context.chapters_dir, self.context.current_chapter_title,
                                                        subtitle)
        self.page_maker.save_current_sub_chapter(content)

        print("injection contenu, id: {}".format(self.context.current_page_id))

    def get_imgs(self):
        imgs = self.driver.find_elements_by_xpath("//img")
        for img in imgs:
            src = img.get_attribute("src")
            alt = img.get_attribute("alt")
            if str(alt).startswith("images/"):
                urllib.request.urlretrieve(url=src, filename=self.context.localdir + "/" + alt)
                print("récupération {}".format(alt))

    def check_chapter(self):
        headtitle = self.driver.find_element_by_class_name("Current.Opened")
        title = headtitle.find_element(By.CSS_SELECTOR, "h2")
        if re.sub(r'([|:?\\\/<>*^])', '', title.text) != self.context.current_chapter_title:
            self.context.current_chapter_title = title.text
            self.context.current_sub_chapter_id = 0
            print("Section {}".format(self.context.current_chapter_title))
            self.context.chapters_names.append(self.context.current_chapter_title)
            self.page_maker.create_new_chapter()
            self.context.sub_chapters_names[self.context.current_chapter_title] = []

    def extract_pages(self):
        self._go_to_first_book_page()
        self.context.previous_url = self.driver.current_url
        self.get_description_book_page()
        self.driver.find_element_by_id("btn_Next").click()
        time.sleep(1)
        current_url = self.driver.current_url
        print(" -------Extraction des pages-----------")
        while current_url != self.context.previous_page_url:
            content = self.driver.find_element_by_class_name("sect1").get_attribute("innerHTML")
            quizz_search = re.findall(r'<h4 class="titleQ">Quiz</h4>', content)
            if quizz_search:
                pass
            else:
                self.check_chapter()
                self.get_page()
                self.get_imgs()
            self.context.previous_page_url = self.driver.current_url
            self.driver.find_element_by_id("btn_Next").click()
            time.sleep(1)
            current_url = self.driver.current_url
        self.driver.close()
        print("fermeture de {}".format(self.driver_path))
        print(" -------Fin d'extraction-----------")


def get_all_books(file_list):
    """
    capte tous les livres de la liste
    """
    with open(file_list, "r", encoding='utf-8') as file:
        books = file.readlines()
    print(books)
    echecs = []
    for book in books:
        try:
            extractor = PageExtractor(book.strip(), hidden_mode=False)
            extractor.extract_pages()
            extractor.page_maker.generate_json_summary()
            extractor.page_maker.reformat_images_src()
        except Exception as e:
            rmtree(book.strip()) if book != "" else None
            echecs.append(book)
            print("impossible de charger %s" % book)
            print(e.args)


    print("echecs :")
    print(echecs)


def get_on_book(book):
    extractor = PageExtractor(book.strip())
    extractor.extract_pages()
    extractor.page_maker.generate_json_summary()
    extractor.page_maker.reformat_images_src()