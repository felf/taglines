import os
import sqlite3
# TODO: remove all output stuff from here
import sys

class Database:
    def __init__(self, dbfilename = None): # {{{1
        self.isOpen = False
        self.db = None
        self.filename = None
        self.filters = {}
        self.exactAuthorMode = False

        if dbfilename: self.setPath(dbfilename)

    def __del__(self): # {{{1
        self.close()
        
    def setPath(self, path):
        """ Sets the instance's database filename.

        If the path is valid, it is stored and True is returned. """

        filename = os.path.abspath(path)
        exists = os.path.exists(filename)
        isfile = os.path.isfile(filename)
        if exists and isfile:
            self.filename = filename
            return True
        else: return False

    def open(self): # {{{1
        """ Opens a connection to an existing database.
            
        Returns False if unsuccessful. """

        if self.isOpen: return
        self.db = sqlite3.connect(self.filename, detect_types=True)
        self.isOpen = type(self.db) is sqlite3.Connection
        # TODO: handle invalid DB
        return self.isOpen

    def initialiseFile(self, filename): # {{{1
        """Initialises a new, empty database"""
        if self.isOpen: self.close()

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
            print("\nError while creating the database file: {0}. Exiting.".format(e.args[0]), file=sys.stderr)
            exit(1)
        except sqlite3.Error as e:
            print("An sqlite3 error occurred:", e.args[0])
        except Exception as e:
            print("\nError while initialising the database file: {0}. Exiting.".format(e.args[0]), file=sys.stderr)
            exit(1)

    def commit(self): # {{{1
        if self.isOpen:
            self.db.commit()

    def close(self): # {{{1
        """ Closes the instance's database connection. """

        if self.db and self.isOpen:
            self.db.commit()
            self.db.close()
            self.db = None
            self.isOpen = False

    def execute(self, query, args=None, commit = False): # {{{1
        if not self.isOpen and not self.open():
            return False
        c = self.db.cursor()
        if args:
            r = c.execute(query, args)
        else:
            r = c.execute(query)
        if commit and query.lower()[0:6] in ("insert", "update", "delete"):
            self.db.commit()
        return r

    def getOne(self, query, args = None): # {{{1
        """ Shortcut function for a simply one-line retrieve. """
        c = self.execute(query, args)
        return c.fetchone() if c else None

    def parseArguments(self, args): # {{{1
        self.filters = {}
        self.exactAuthorMode = args.exactauthor
        self.tagsOrMode = args.ortag
        if args.author: self.filters["author"] = args.author
        if args.tag: self.filters["tags"] = args.tag
        if args.lang: self.filters["language"] = args.lang

    def randomTagline(self): # {{{1
        c = self.taglines(True)
        if c:
            return c.fetchone()[0]

    def taglines(self, random = False): # {{{1
        """ Returns taglines according to set filters. """

        query="SELECT text FROM lines l, taglines tl"
        qargs=[]

        author = self.filters.get("author")
        if author:
            if self.exactAuthorMode:
                query += " JOIN authors a ON a.name=? AND tl.author=a.id"
                qargs.append(author)
            else:
                query += " JOIN authors a ON a.name LIKE ? AND tl.author=a.id"
                qargs.append("%"+author+"%")

        tags = self.filters.get("tags")
        if tags:
            qtags=["tag t{0}".format(x) for x in range(len(tags))]
            if self.tagsOrMode:
                tagquery=("SELECT t1.tagline FROM tag t1 JOIN tags s1 ON t1.tag=s1.id WHERE (" +
                        " OR ".join(["s1.text=?"]*len(tags)) + ")")
            else:
                qwhere=["t{0}='{1}'".format(x,tags[x]) for x in range(len(tags))]
                tagquery=("SELECT t1.tagline FROM " +
                    " JOIN ".join([
                    "tag t{0}, tags s{0} on s{0}.id=t{0}.tag AND s{0}.text=? AND t1.tagline=t{0}.tagline".format(x+1,tags[x]) for x in range(len(tags))])
                    )
            qargs += tags
        else: tagquery=None

    #    query="SELECT text FROM lines l, taglines tl"

        query += " WHERE tl.id=l.tagline"
        if tagquery:
            query += " AND tl.id IN ("+tagquery+")"

        lang = self.filters.get("language")
        if lang:
            query += " AND l.language=?"
            qargs.append(lang)

        if random:
            query += " ORDER BY RANDOM() LIMIT 1"

        return self.execute(query, (qargs))

    def tags(self, orderByName = True): # {{{1
        query = "SELECT text FROM tags"
        if orderByName:
            query += " ORDER by text"
        return (r[0] for r in self.execute(query))

    def authors(self, orderByName = True): # {{{1
        query = "SELECT name, born, died FROM authors ORDER BY name"
        return (name+(" ({0}-{1})".format(born,died) if born or died else "")
                for name,born,died in self.execute(query))

    def stats(self): # {{{1
        stats = {}
        stats["tag assignments"] = int(self.getOne("SELECT count(*) FROM tag")[0])
        stats["tag count"] = int(self.getOne("SELECT count(*) FROM tags")[0])
        stats["tagline count"] = int(self.getOne("SELECT count(*) FROM taglines")[0])
        stats["line count"] = int(self.getOne("SELECT count(*) FROM lines")[0])
        stats["author count"] = int(self.getOne("SELECT count(*) FROM authors")[0])
        stats["language count"] = int(self.getOne("SELECT COUNT(*) FROM (SELECT DISTINCT language FROM lines)")[0])

        c = self.execute("SELECT text FROM lines")
        linelengthsum = sum(len(r[0]) for r in c)
        stats["avg tagline length"] = linelengthsum/stats["line count"]

        return stats
