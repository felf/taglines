""" Encapsulation of tagline data in an sqlite database file. """

from __future__ import print_function
import os
import sqlite3
from datetime import date


class Database:  # {{{1
    """ General management of the database. """

    class DatabaseError(Exception):  # {{{2
        """ Exception that is thrown if an error with sqlite occurs. """

        def __init__(self, message):
            super(Database.DatabaseError, self).__init__()
            self.args = (message,)

    def __init__(self, dbfilename=None):  # {{{2
        self.is_open = False
        self.db = None
        self.filename = None
        self.filters = {}
        self.exact_author = False
        self.keywords_or = False

        if dbfilename and not self.set_path(dbfilename):
            raise Exception("The given filename could not be opened.")

    def __del__(self):  # {{{2
        self.close()

    def set_path(self, path):  # {{{2
        """ Sets the instance's database filename.

        If the path is valid, it is stored and True is returned. """

        filename = os.path.abspath(path)
        exists = os.path.exists(filename)
        isfile = os.path.isfile(filename)
        if exists and isfile:
            self.filename = filename
            return True
        else:
            return False

    def open(self):  # {{{2
        """ Opens a connection to an existing database.

        Returns False if unsuccessful. """

        if self.is_open:
            return
        self.db = sqlite3.connect(self.filename, detect_types=True)
        self.is_open = isinstance(self.db, sqlite3.Connection)
        # TODO: handle invalid DB
        return self.is_open

    def initialise_file(self, filename):  # {{{2
        """Initialises a new, empty database"""

        if self.is_open:
            self.close()

        try:
            dbfile = open(filename, 'w')
            dbfile.close()
            self.filename = filename
            self.db = sqlite3.connect(self.filename)
            cursor = self.db.cursor()
            #db.text_factory=str
            cursor.execute('CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT, born INT DEFAULT NULL, died INT DEFAULT NULL);')
            cursor.execute('CREATE TABLE lines (id INTEGER PRIMARY KEY, tagline INT, date DATE, language VARCHAR(5), text TEXT);')
            # the keyword-tagline assignment table
            cursor.execute('CREATE TABLE kw_tl (id INTEGER PRIMARY KEY, keyword INT, tagline INT);')
            cursor.execute('CREATE TABLE taglines (id INTEGER PRIMARY KEY, author INT, source TEXT DEFAULT NULL, remark TEXT DEFAULT NULL, date DATE DEFAULT NULL);')
            cursor.execute('CREATE TABLE keywords (id INTEGER PRIMARY KEY, text TEXT UNIQUE);')
            self.db.commit()
            self.is_open = True
        except IOError as error:
            raise Database.DatabaseError("Error creating database file: {}".format(error.args[0]))
        except sqlite3.Error as error:
            raise Database.DatabaseError("An sqlite3 error occurred: {}".format(error.args[0]))

    def commit(self):  # {{{2
        """ Save any changes to the database that have not yet been committed. """

        if self.is_open:
            self.db.commit()

    def close(self):  # {{{2
        """ Closes the instance's database connection. """

        if self.db and self.is_open:
            self.db.commit()
            self.db.close()
            self.db = None
            self.is_open = False

    def execute(self, query, args=None, commit=False, debug=False):  # {{{2
        """ Execute a query on the database and evaluate the result. """

        if not self.is_open and not self.open():
            return False
        cursor = self.db.cursor()
        if debug:
            print(query)
        if args:
            if debug:
                print(args)
            try:
                row = cursor.execute(query, args)
            except (sqlite3.OperationalError, sqlite3.InterfaceError):
                print("Query:", query)
                print("args:", args)
                raise
        else:
            row = cursor.execute(query)
        if commit and query.lower()[0:6] in ("insert", "update", "delete"):
            self.db.commit()
        return row

    def get_one(self, query, args=None):  # {{{2
        """ Shortcut function for a simply one-line retrieve. """

        cursor = self.execute(query, args)
        return cursor.fetchone() if cursor else None

    def parse_arguments(self, args):  # {{{2
        """ Evaluate given arguments and set appropriate option variables. """

        self.filters = {}
        self.exact_author = args.exactauthor
        self.keywords_or = args.orkeyword
        if args.author:
            self.filters["author"] = args.author
        if args.keyword:
            self.filters["keywords"] = args.keyword
        if args.lang:
            self.filters["language"] = args.lang
        if args.text:
            self.filters["text"] = args.text

    def random_tagline(self):  # {{{2
        """ Retrieve and return a random tagline text from the database. """

        cursor = self.taglines(True)
        if cursor:
            return cursor.fetchone()[0]

    def taglines(self, random=False):  # {{{2
        """ Retrieve and return taglines according to set filters. """

        query = "SELECT text FROM lines AS l"
        qargs = []
        where = []

        author = self.filters.get("author")
        if author:
            query += " JOIN taglines AS tl ON l.tagline=tl.id"
            if self.exact_author:
                query += " JOIN authors a ON a.name=? AND tl.author=a.id"
                qargs.append(author)
            else:
                query += " JOIN authors a ON a.name LIKE ? AND tl.author=a.id"
                qargs.append("%" + author + "%")

        keywords = self.filters.get("keywords")
        if keywords:
            where.append(
                """l.tagline IN (
                SELECT tagline FROM kw_tl JOIN keywords ON kw_tl.keyword=keywords.id WHERE text IN ({keyword_texts}) GROUP BY tagline{having}
                )""".format(
                    keyword_texts=",".join(["?"] * len(keywords)),
                    having="" if self.keywords_or else " HAVING count(*)=?",
                ))
            qargs += keywords
            if not self.keywords_or:
                qargs.append(len(keywords))

        text = self.filters.get("text")
        if text:
            where.extend(["text like ?"] * len(text))
            for keyword in text:
                if not keyword.startswith('%') and not keyword.endswith('%'):
                    keyword = '%' + keyword + '%'
                qargs.append(keyword)

        lang = self.filters.get("language")
        if lang:
            where.append("l.language=?")
            qargs.append(lang)

        if where:
            query += " WHERE " + " AND ".join(where)

        if random:
            query += " ORDER BY RANDOM() LIMIT 1"

        return self.execute(query, (qargs))

    def keywords(self, by_name=True):  # {{{2
        """ Retrieve and return all keywords and their names from the db. """

        query = "SELECT text FROM keywords"
        if by_name:
            query += " ORDER by text"
        return (row[0] for row in self.execute(query))

    def authors(self, by_name=True):  # {{{2
        """ Retrieve and return all authors and their data from the database. """

        query = "SELECT name, born, died FROM authors"
        if by_name:
            query += " ORDER BY name"
        return (name+(" ({}-{})".format(
            born if born else "",
            died if died else ""
            ) if born or died else "") for name, born, died in self.execute(query))

    def stats(self):  # {{{2
        """ Calculate and return some statistical data on the database. """

        stats = {}
        stats["keyword assignments"] = int(self.get_one("SELECT count(*) FROM kw_tl")[0])
        stats["keyword count"] = int(self.get_one("SELECT count(*) FROM keywords")[0])
        stats["tagline count"] = int(self.get_one("SELECT count(*) FROM taglines")[0])
        stats["line count"] = int(self.get_one("SELECT count(*) FROM lines")[0])
        stats["author count"] = int(self.get_one("SELECT count(*) FROM authors")[0])
        stats["language count"] = int(self.get_one(
            "SELECT COUNT(*) FROM (SELECT DISTINCT language FROM lines)")[0])

        cursor = self.execute("SELECT text FROM lines")
        linelengthsum = sum(len(row[0]) for row in cursor)
        stats["avg tagline length"] = linelengthsum/stats["line count"] if \
                stats["line count"] != 0 else 0

        return stats


class DatabaseTagline:  # {{{1
    """ Encapsulate a tagline in the database. """

    def __init__(self, db, tagline_id=None, author=None, keywords=None):  # {{{2
        """ Initialise data values depending on given id.

        @param _db: Handle to the sqlite database.
        @param _id: The ID of the tagline in the database.
                    If _id is None, the object is initialised empty. """

        self.db = db
        self.id = tagline_id
        self.is_changed = False

        if self.id is None:
            self.author = author
            self.author_name = None
            self.source = None
            self.remark = None
            self.when = None
            # pylint says keywords=set() in function interface is dangerous
            self.keywords = set() if keywords is None else keywords
            self.texts = {}
        else:
            cursor = self.db.execute(
                """SELECT author, name, source, remark, date
                    FROM taglines AS t LEFT JOIN authors AS a ON a.id=t.author
                    WHERE t.id=?""",
                (self.id,))
            row = cursor.fetchone()
            if row:
                self.author = row[0]
                self.author_name = row[1]
                self.source = row[2]
                self.remark = row[3]
                self.when = row[4]
            self.texts = {}

            cursor = self.db.execute(
                "SELECT keyword FROM kw_tl WHERE tagline=?", (self.id,))
            self.keywords = set(keyword[0] for keyword in cursor)

            cursor = self.db.execute(
                "SELECT language, text FROM lines WHERE tagline=?", (self.id,))
            for row in cursor:
                self.texts[row[0]] = [row[1], False]

        # todo
        #self.last_changed = None

    def get_texts(self):
        """ Return a dict {language: text} from the internal list.

        The difference to self.texts is that the latter also contains a flag to
        store the changed state. """

        return {language: self.texts[language][0] for language in self.texts}

    def get_text(self, language):  # {{{2
        """ Retrieve the text with the given language from the internal list. """

        text = self.texts.get(language, None)
        if text is None:
            return None
        return text[0]

    def pop_text(self, language):  # {{{2
        """ Retrieve and remove the text with the given language from the internal list. """

        text = self.texts.pop(language, None)
        if text is None:
            return None
        self.is_changed = True
        return text[0]

    def set_text(self, language, text, old_language=None):  # {{{2
        """ Add a new text item for the given language.

        If old_language is given, replace it by the new item. """

        old_text = self.texts.get(language, None)
        if old_text is not None:
            if old_text[0] == text:
                return
        if old_language is not None:
            if old_language != language:
                self.texts.pop(old_language)
        self.texts[language] = [text, True]
        self.is_changed = True

    def text(self, language):  # {{{2
        """ Get tagline text associated with the given language. """

        return self.texts.get(language, None)

    def set_information(self, source, remark, when):  # {{{2
        """ Assign values to the tagline's source, remark and date field. """

        if source == "":
            source = None
        if remark == "":
            remark = None
        if when == "":
            when = None
        self.is_changed = (self.source != source or
                           self.remark != remark or
                           self.when != when)
        self.source = source
        self.remark = remark
        self.when = when
        #TODO: set changed

    def commit(self):  #{{{2
        """ Write changed data to database. """

        if self.id is None:
            cursor = self.db.execute(
                "INSERT INTO taglines (author,source,remark,date) VALUES (?,?,?,?)", (
                    self.author,
                    self.source if self.source != "" else None,
                    self.remark if self.remark != "" else None,
                    self.when if self.when != "" else None))
            self.id = cursor.lastrowid

            present_languages = set()
            present_keywords = set()
        else:
            cursor = self.db.execute(
                "UPDATE taglines set author=?, source=?, remark=?, date=? WHERE id=?", (
                    self.author, self.source, self.remark, self.when, self.id))

            cursor = self.db.execute("SELECT language FROM lines WHERE tagline=?", (self.id,))
            present_languages = set(item[0] for item in cursor)

            cursor = self.db.execute("SELECT keyword FROM kw_tl WHERE tagline=?", (self.id,))
            present_keywords = set(item[0] for item in cursor)

        for lang in self.texts:
            if lang in present_languages:
                if self.texts[lang][1]:
                    self.db.execute(
                        "UPDATE lines set date=?, text=? WHERE tagline=? AND language=?",
                        (date.today().isoformat(), self.texts[lang][0], self.id, lang))
                present_languages.remove(lang)
            else:
                self.db.execute(
                    "INSERT INTO lines (tagline, date, language, text) VALUES (?,?,?,?)",
                    (self.id, date.today().isoformat(), lang, self.texts[lang][0]))
            self.texts[lang][1] = False
        for lang in present_languages:
            self.db.execute("DELETE FROM lines WHERE tagline=? AND language=?", (self.id, lang))

        for keyword in self.keywords:
            if keyword in present_keywords:
                present_keywords.remove(keyword)
            else:
                self.db.execute("INSERT INTO kw_tl (keyword, tagline) VALUES (?,?)", (keyword, self.id))
        for keyword in present_keywords:
            self.db.execute("REMOVE FROM kw_tl WHERE keyword=? AND tagline=?", (keyword, self.id))

        self.db.commit()
        self.is_changed = False
