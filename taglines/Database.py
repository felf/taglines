""" Encapsulation of tagline data in an sqlite database file. """

from __future__ import print_function
import os
import sqlite3
# TODO: remove all output stuff from here
import sys


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
