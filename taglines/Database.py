""" Encapsulation of tagline data in an sqlite database file. """

from __future__ import print_function
import os
import sqlite3
# TODO: remove all output stuff from here
import sys
from datetime import date


class Database:  # {{{1
    """ General management of the database. """

    def __init__(self, dbfilename=None):  # {{{2
        self.isOpen = False
        self.db = None
        self.filename = None
        self.filters = {}
        self.exactAuthorMode = False
        self.tagsOrMode = False

        if dbfilename and not self.setPath(dbfilename):
            raise Exception("The given filename could not be opened.")

    def __del__(self):  # {{{2
        self.close()

    def setPath(self, path):  # {{{2
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

        if self.isOpen:
            return
        self.db = sqlite3.connect(self.filename, detect_types=True)
        self.isOpen = isinstance(self.db, sqlite3.Connection)
        # TODO: handle invalid DB
        return self.isOpen

    def initialiseFile(self, filename):  # {{{2
        """Initialises a new, empty database"""

        if self.isOpen:
            self.close()

        try:
            dbfile = open(filename, 'w')
            dbfile.close()
            self.filename = filename
            self.db = sqlite3.connect(self.filename)
            c = self.db.cursor()
            #db.text_factory=str
            c.execute('CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT, born INT DEFAULT NULL, died INT DEFAULT NULL);')
            c.execute('CREATE TABLE lines (id INTEGER PRIMARY KEY, tagline INT, date DATE, language VARCHAR(5), text TEXT);')
            c.execute('CREATE TABLE tag (id INTEGER PRIMARY KEY, tag INT, tagline INT);')
            c.execute('CREATE TABLE taglines (id INTEGER PRIMARY KEY, author INT, source TEXT DEFAULT NULL, remark TEXT DEFAULT NULL, date DATE DEFAULT NULL);')
            c.execute('CREATE TABLE tags (id INTEGER PRIMARY KEY, text TEXT UNIQUE);')
            self.db.commit()
            self.isOpen = True
        except IOError as e:
            print("\nError while creating the database file: {}. Exiting.".
                  format(e.args[0]), file=sys.stderr)
            exit(1)
        except sqlite3.Error as e:
            print("An sqlite3 error occurred:", e.args[0])

    def commit(self):  # {{{2
        """ Save any changes to the database that have not yet been committed. """

        if self.isOpen:
            self.db.commit()

    def close(self):  # {{{2
        """ Closes the instance's database connection. """

        if self.db and self.isOpen:
            self.db.commit()
            self.db.close()
            self.db = None
            self.isOpen = False

    def execute(self, query, args=None, commit=False, debug=False):  # {{{2
        """ Execute a query on the database and evaluate the result. """

        if not self.isOpen and not self.open():
            return False
        c = self.db.cursor()
        if debug:
            print(query)
        if args:
            if debug:
                print(args)
            try:
                r = c.execute(query, args)
            except (sqlite3.OperationalError, sqlite3.InterfaceError):
                print("Query:", query)
                print("args:", args)
                raise
        else:
            r = c.execute(query)
        if commit and query.lower()[0:6] in ("insert", "update", "delete"):
            self.db.commit()
        return r

    def getOne(self, query, args=None):  # {{{2
        """ Shortcut function for a simply one-line retrieve. """

        c = self.execute(query, args)
        return c.fetchone() if c else None

    def parseArguments(self, args):  # {{{2
        """ Evaluate given arguments and set appropriate option variables. """

        self.filters = {}
        self.exactAuthorMode = args.exactauthor
        self.tagsOrMode = args.ortag
        if args.author:
            self.filters["author"] = args.author
        if args.tag:
            self.filters["tags"] = args.tag
        if args.lang:
            self.filters["language"] = args.lang

    def randomTagline(self):  # {{{2
        """ Retrieve and return a random tagline text from the database. """

        c = self.taglines(True)
        if c:
            return c.fetchone()[0]

    def taglines(self, random=False):  # {{{2
        """ Retrieve and return taglines according to set filters. """

        query = "SELECT text FROM lines AS l"
        qargs = []
        where = False

        author = self.filters.get("author")
        if author:
            query += " JOIN taglines AS tl ON l.tagline=tl.id"
            if self.exactAuthorMode:
                query += " JOIN authors a ON a.name=? AND tl.author=a.id"
                qargs.append(author)
            else:
                query += " JOIN authors a ON a.name LIKE ? AND tl.author=a.id"
                qargs.append("%" + author + "%")

        tags = self.filters.get("tags")
        if tags:
            query += """ WHERE l.tagline IN (
                SELECT tagline FROM tag JOIN tags ON tag.tag=tags.id WHERE text IN ({tag_texts}) GROUP BY tagline{having}
            )""".format(
                tag_texts=",".join(["?"] * len(tags)),
                having="" if self.tagsOrMode else " HAVING count(*)=?",
                )
            qargs += tags
            if not self.tagsOrMode:
                qargs.append(len(tags))
            where = True

        lang = self.filters.get("language")
        if lang:
            query += "{} l.language=?".format(" AND" if where else " WHERE")
            where = True
            qargs.append(lang)

        if random:
            query += " ORDER BY RANDOM() LIMIT 1"

        return self.execute(query, (qargs))

    def tags(self, orderByName=True):  # {{{2
        """ Retrieve and return all tags and their names from the database. """

        query = "SELECT text FROM tags"
        if orderByName:
            query += " ORDER by text"
        return (r[0] for r in self.execute(query))

    def authors(self, orderByName=True):  # {{{2
        """ Retrieve and return all authors and their data from the database. """

        query = "SELECT name, born, died FROM authors"
        if orderByName:
            query += " ORDER BY name"
        return (name+(" ({}-{})".format(
            born if born else "",
            died if died else ""
            ) if born or died else "") for name, born, died in self.execute(query))

    def stats(self):  # {{{2
        """ Calculate and return some statistical data on the database. """

        stats = {}
        stats["tag assignments"] = int(self.getOne("SELECT count(*) FROM tag")[0])
        stats["tag count"] = int(self.getOne("SELECT count(*) FROM tags")[0])
        stats["tagline count"] = int(self.getOne("SELECT count(*) FROM taglines")[0])
        stats["line count"] = int(self.getOne("SELECT count(*) FROM lines")[0])
        stats["author count"] = int(self.getOne("SELECT count(*) FROM authors")[0])
        stats["language count"] = int(self.getOne("SELECT COUNT(*) FROM (SELECT DISTINCT language FROM lines)")[0])

        c = self.execute("SELECT text FROM lines")
        linelengthsum = sum(len(r[0]) for r in c)
        stats["avg tagline length"] = linelengthsum/stats["line count"] if \
                stats["line count"] != 0 else 0

        return stats


class DatabaseTagline:  # {{{1
    """ Encapsulate a tagline in the database. """

    def __init__(self, db, tagline_id=None, author=None, tags=None):  # {{{2
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
            # pylint: tags=set() in function interface is dangerous
            self.tags = set() if tags is None else tags
            self.texts = {}
        else:
            c = self.db.execute(
                """SELECT author, name, source, remark, date
                    FROM taglines AS t LEFT JOIN authors AS a ON a.id=t.author
                    WHERE t.id=?""",
                (self.id,))
            row = c.fetchone()
            if row:
                self.author = row[0]
                self.author_name = row[1]
                self.source = row[2]
                self.remark = row[3]
                self.when = row[4]
            self.texts = {}

            c = self.db.execute(
                "SELECT tag FROM tag WHERE tagline=?", (self.id,))
            self.tags = set(tag[0] for tag in c)

            c = self.db.execute(
                "SELECT language, text FROM lines WHERE tagline=?", (self.id,))
            for row in c:
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
        self.is_changed = self.source != source or \
                          self.remark != remark or \
                          self.when != when
        self.source = source
        self.remark = remark
        self.when = when
        #TODO: set changed

    def commit(self):  #{{{2
        """ Write changed data to database. """

        if self.id is None:
            c = self.db.execute("INSERT INTO taglines (author,source,remark,date) VALUES (?,?,?,?)", (
                self.author,
                self.source if self.source != "" else None,
                self.remark if self.remark != "" else None,
                self.when if self.when != "" else None))
            self.id = c.lastrowid

            present_languages = set()
            present_tags = set()
        else:
            c = self.db.execute("UPDATE taglines set author=?, source=?, remark=?, date=?", (
                self.author, self.source, self.remark, self.when))

            c = self.db.execute("SELECT language FROM lines WHERE tagline=?", (self.id,))
            present_languages = set(item[0] for item in c)

            c = self.db.execute("SELECT tag FROM tag WHERE tagline=?", (self.id,))
            present_tags = set(item[0] for item in c)

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

        for t in self.tags:
            if t in present_tags:
                present_tags.remove(t)
            else:
                self.db.execute("INSERT INTO tag (tag, tagline) VALUES (?,?)", (t, self.id))
        for t in present_tags:
            self.db.execute("REMOVE FROM tag WHERE tag=? AND tagline=?", (t, self.id))

        self.db.commit()
        self.is_changed = False
