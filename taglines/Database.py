import os
import sqlite3
# TODO: remove all output stuff from here
import sys

class Database:
    def __init__(self, dbfilename = None): # {{{1
        self.isOpen = False
        self.db = None
        self.filename = None
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

    def initialiseFile(self, filename):
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

    def execute(self, query, args=None, commit = False):
        if not self.isOpen: return
        c = self.db.cursor()
        if args:
            r = c.execute(query, args)
        else:
            r = c.execute(query)
        if commit and query.lower()[0:6] in ("insert", "update", "delete"):
            self.db.commit()
        return r
