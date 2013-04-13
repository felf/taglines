import os
import sqlite3

class Database:
    def __init__(self, dbfilename): # {{{1
        self.isOpen = False
        self.db = None
        self.setPath(dbfilename)

    def __del__(self): # {{{1
        self.close()
        
    def setPath(self, path):
        """ Sets the instance's database filename.

        If the path is valid, it is stored and True is returned. """

        filename = os.path.abspath(path)
        exists = os.path.exists(filename)
        isfile = os.path.isfile(filename)
        if exists and isfile:
            self.dbfilename = filename
            return True
        else: return False

    def open(self, filename = None): # {{{1
        """ Opens a connection to an existing database.
            
        Returns False if unsuccessful. """

        if self.isOpen: return
        if not self.setPath(filename if filename else self.dbfilename):
            return False

        self.db = sqlite3.connect(self.dbfilename, detect_types=True)
        self.isOpen = type(self.db) is sqlite3.Connection
        # TODO: handle invalid DB
        return self.isOpen

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
