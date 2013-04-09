#!/usr/bin/python3
# -*- coding: utf-8 -*-

# digest options {{{1
# ----------------------------------------------------------------
import argparse
parser = argparse.ArgumentParser(
        description='An sqlite3 based taglines generator and manager.',
        prog="Taglines.py")

group=parser.add_mutually_exclusive_group()
group.add_argument('-L', '--list', action='store_true', help='List all found items')
group.add_argument('-r', '--random', action='store_true', help='From the found items, show one at random (default)')
group.add_argument('--show-tags', action='store_true', help='List all available tags in the database and exit')
group.add_argument('--show-authors', action='store_true', help='List all available authors in the database and exit')
group.add_argument('--stats', action='store_true', help='Show some statistics about the database')
group.add_argument('--init', action='store_true', help='Initialise a new database file')
group.add_argument('-i', '--interactive', action='store_true', help='Go into interactive mode (simple shell)')
parser.add_argument('-o', '--ortag', action='store_true', help='Combine several tags with OR instead of AND')
parser.add_argument('-t', '--tag', action='append', help='Only show items with the given tag')
parser.add_argument('-a', '--author', help='Only show items by the given author')
parser.add_argument('-e', '--exactauthor', action='store_true', help='Look for exact author match')
parser.add_argument('-l', '--lang',  help='Only show items with the given language')
parser.add_argument('-s', '--sort', choices=['a', 'l', 't'], help='Sort output by author, language or text')
parser.add_argument('file', help='An sqlite3 database file')

#group=parser.add_argument_group('Actions')
#group=parser.add_mutually_exclusive_group()

args=parser.parse_args()
#}}}1

# imports {{{1
import os
#import datetime
from datetime import date
import sqlite3
import sys
#}}}1

# create a new sqlite database file {{{1
# ----------------------------------------------------------------
def db_initialise_file():
    """Initialises a new, empty database"""
    try:
        dbfile=open( args.file, 'w' )
        dbfile.close()
        print("Creating new database file...", end=' ')
        db=sqlite3.connect( args.file )
        #db.text_factory=str
        db.execute('CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT, born INT DEFAULT NULL, died INT DEFAULT NULL);')
        db.execute('CREATE TABLE lines (id INTEGER PRIMARY KEY, tagline INT, date DATE, language VARCHAR(5), text TEXT);')
        db.execute('CREATE TABLE tag (id INTEGER PRIMARY KEY, tag INT, tagline INT);')
        db.execute('CREATE TABLE taglines (id INTEGER PRIMARY KEY, author INT, source TEXT DEFAULT NULL, remark TEXT DEFAULT NULL, date DATE DEFAULT NULL);')
        db.execute('CREATE TABLE tags (id INTEGER PRIMARY KEY, text TEXT UNIQUE);')
        db.commit()
        print("done.")
    except IOError as e:
        print("\nError while creating the database file: {0}. Exiting.".format(e.args[0]), file=sys.stderr)
        exit(1)
    except sqlite3.Error as e:
        print("An sqlite3 error occurred:", e.args[0])
    except:
        print("\nError while initialising the database file: {0}. Exiting.".format(e.args[0]), file=sys.stderr)
        exit(1)

if args.init:
    if os.path.exists(args.file):
        ok = input("Warning: "+args.file+" already exists. Overwrite? [y/N] ")
        if ok and "yes".startswith(ok.lower()):
            try:
                os.remove( args.file )
            except OSError as e:
                print("Error: could not delete old file: {0}. Exiting.".format(e.args[1]), file=sys.stderr)
                exit(1)
        else:
            print("good bye")
            exit(1)
    db_initialise_file()
    exit(0)


# get database handle from file {{{1
# ----------------------------------------------------------------
def get_database_from_file(path):
    if path is None:
        print("Error: no path to database given. Exiting.", file=sys.stderr)
        exit(1)

    args.file=os.path.abspath( path )
    fileexists=os.path.exists( path )
    validfile=os.path.isfile( path ) if fileexists else True

    if not validfile:
        print("Error: the given path is not a valid file. Exiting.", file=sys.stderr)
        exit(1)

    if not fileexists and not args.init:
        print("Error: the given file does not exist. Exiting.", file=sys.stderr)
        exit(1)

    try:
        db=sqlite3.connect(path, detect_types=True)
        return db
    except:
        print("Error: could not open database file. Exiting.", file=sys.stderr)
        exit(1)


# retrieve one random tagline, then exit {{{1
if args.random or args.list:
    db = get_database_from_file(args.file);
    query="SELECT text FROM lines l, taglines tl"
    qargs=[]

    if args.author:
        # TODO: LIKE und c.execute mit ? unter einen Hut bringen
        if args.exactauthor:
            query+=" JOIN authors a ON a.name=? AND tl.author=a.id"
            qargs.append(args.author)
        else:
            query+=" JOIN authors a ON a.name LIKE '%{0}%' AND tl.author=a.id".format(args.author)
            #qargs.append(args.author)

    if args.tag:
        qtags=["tag t{0}".format(x) for x in range(len(args.tag))]
        if args.ortag:
            tagquery=("SELECT t1.tagline FROM tag t1 JOIN tags s1 ON t1.tag=s1.id WHERE (" +
                    " OR ".join(["s1.text=?"]*len(args.tag)) + ")")
        else:
            qwhere=["t{0}='{1}'".format(x,args.tag[x]) for x in range(len(args.tag))]
            tagquery=("SELECT t1.tagline FROM " +
                " JOIN ".join([
                "tag t{0}, tags s{0} on s{0}.id=t{0}.tag AND s{0}.text=? AND t1.tagline=t{0}.tagline".format(x+1,args.tag[x]) for x in range(len(args.tag))])
                )
        qargs+=args.tag
    else: tagquery=None

#    query="SELECT text FROM lines l, taglines tl"

    query+=" WHERE tl.id=l.tagline"
    if tagquery:
        query+=" AND tl.id IN ("+tagquery+")"

    if args.lang:
        query+=" AND l.language=?"
        qargs.append(args.lang)

    if args.random:
        query+=" ORDER BY RANDOM() LIMIT 1"

    first=True
    for r in db.execute(query, (qargs)):
        if first:
            first=False
        else:
            print("%")
        print(r[0])
    exit(0)


# stand-alone DB functions {{{1
# ----------------------------------------------------------------
if args.show_tags:
    db = get_database_from_file(args.file);
    for row in db.execute( "SELECT text FROM tags ORDER BY text" ):
        print(row[0])
    exit(0)


if args.show_authors:
    db = get_database_from_file(args.file);
    for row in db.execute( "SELECT name, born, died FROM authors ORDER BY name" ):
        out=row[0]
        if row[1] is not None or row[2] is not None:
            out+=" ("+str(row[1])+"-"+str(row[2])+")"
        print(out)
    exit(0)

if args.stats:
    db = get_database_from_file(args.file);
    c=db.cursor()
    c.execute( "SELECT count(*) FROM tag" )
    r=c.fetchone()
    tagnumber=r[0];

    c.execute( "SELECT count(*) FROM tags" )
    r=c.fetchone()
    tagsnumber=r[0];

    c.execute( "SELECT count(*) FROM taglines" )
    r=c.fetchone()
    taglinesnumber=r[0];

    c.execute( "SELECT count(*) FROM lines" )
    r=c.fetchone()
    linesnumber=r[0];

    c.execute( "SELECT count(*) FROM authors" )
    r=c.fetchone()
    authorsnumber=r[0];

    c.execute( "SELECT COUNT(*) FROM (SELECT DISTINCT language FROM lines)" )
    r=c.fetchone()
    languages=r[0]

    c.execute( "SELECT text FROM lines" )
    length=0
    for r in c:
        length+=len(r[0])

    print("Number of taglines:        {0:6d}".format(taglinesnumber,))
    print("Number of texts:           {0:6d}   (ø {1:5.2f} per tagline)".format(
        linesnumber, linesnumber/taglinesnumber))
    print("Average text length:       {0:8.1f}".format(length/linesnumber,))
    print("Number of tags:            {0:6d}".format(tagsnumber,))
    print("Number of tag assignments: {0:6d}   (ø {1:5.2f} per tagline)".format(
        tagnumber, tagnumber/taglinesnumber))
    print("Number of authors:         {0:6d}".format(authorsnumber,))
    print("Used languages:            {0:6d}".format(languages,))
    exit(0)


class CShellmode: #{{{1 interactive mode
    """ Shellmode class

    It provides a hierarchy of menus which are used to inspect
    and modify the content of the database."""

    def __init__(self):
        self.currentAuthor=None
        self.currentTags=[]
        self.db = get_database_from_file(args.file)
        self.c = self.db.cursor()

    def getInput(self, text=""):
        """ This is a common function to get input and catch Ctrl+C/D. """
        while True:
            try:
                return input(text)
            # Ctrl+C
            except KeyboardInterrupt:
                self.exitTaglines()
            # Ctrl+D
            except EOFError:
                return False

    def askYesNo(self, text, default = "n"):
        """ Ask a yes/no question, digest the answer and return the answer.

        default should be either "y" or "n" to set the relevant answer. """

        while True:
            suffix = "  [{0}/{1}] ".format(
                    "Y" if default=="y" else "y",
                    "N" if default=="n" else "n")
            i = self.getInput(text + suffix)
            if not i:
                i = default
            if i:
                if "yes".startswith(i.lower()): i = "y"
                elif "no".startswith(i.lower()): i = "n"
                else: i = ""
            if i == "":
                print("Please answer yes or no.")
            else: return i

    def exitTaglines(self):
        try:
            # not using askYesNo b/c of own handling of Ctrl+C/D
            ok=input("\nReally quit Taglines?  [y/N] ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if ok and "yes".startswith(ok.lower()):
            print("bye")
            sys.exit();

    def authorMenu(self): #{{{2
        """The menu with which to alter author information."""
        i="h"
        while True:
            print()
            if i=="h":
                print("a - add author       l - list all authors")
                print("d - delete author    c - set current author for new taglines")
                print("h - help")
                print("q - quit menu        Q - quit Taglines")
            i=self.getInput("AUTHOR menu selection: ")
            if not i: continue

            if i=="l":
                print("\nALL AUTHORS (sorted by name):")
                self.c.execute( "SELECT id, name, born, died FROM authors ORDER BY name" )
                for row in self.c:
                    out="{0:>4}{1}: {2}".format(row[0], '*' if self.currentAuthor==row[0] else ' ', row[1])
                    if row[2] is not None or row[3] is not None:
                        out+=" ("+str(row[2])+"-"+str(row[3])+")"
                    print(out)
            elif i=="a":
                name=self.getInput("\nName (empty to abort): ")
                # TODO: validate input
                if name!="":
                    try:
                        born=int(self.getInput("Year of birth: "))
                    except ValueError:
                        born=None
                    try:
                        died=int(self.getInput("Year of death: "))
                    except ValueError:
                        died=None
                    try:
                        self.c.execute( "INSERT INTO authors (name, born, died) VALUES (?,?,?)", (
                            name, born, died) )
                        self.db.commit()
                        print("Author added, new ID is {0}".format(self.c.lastrowid))
                    except sqlite3.Error as e:
                        print("An sqlite3 error occurred:", e.args[0])
                    except Exception as e:
                        print("Error while adding author:", e.args[0])

            elif i=="d":
                id=self.getInput("\nID to delete (empty to abort): ")
                if id:
                    try:
                        id=int(id)
                        self.c.execute( 'DELETE FROM authors WHERE id=?', (id,) )
                        self.db.commit()
                        print("Author deleted.")
                    except ValueError:
                        print("Error: no integer ID.")
                    except Exception as e:
                        print("Error while deleting author: {0}.".format(e.args[0],))
            elif i=="c":
                id=self.getInput("\nID of new current author (empty to abort, 'u' to unset): ")
                if id:
                    if id=="u":
                        self.currentAuthor=None
                    else:
                        try:
                            self.c.execute("SELECT id FROM authors WHERE id=?", (id,))
                            if self.c.fetchone() is None:
                                print("Error: no valid ID.")
                            else:
                                self.currentAuthor=int(id)
                        except ValueError:
                            print("Error: no integer ID.")
            elif i=="q":
                return
            elif i=="Q":
                self.exitTaglines()
            else: i="h"

    def tagMenu(self): #{{{2
        """The menu with which to alter tag information."""
        i="h"
        while True:
            print()
            if i=="h":
                print("a - add tag       l - list all tags")
                print("d - delete tag    t - toggle tag (or simply enter the ID)")
                print("h - help")
                print("q - quit menu     Q - quit Taglines")
            i=self.getInput("TAGS menu selection: ")

            # Abkürzung: statt "t" und dann ID eingeben einfach nur die ID
            try:
                id=int(i)
                i="t"
            except ValueError:
                id=None

            if i=="l":
                print("\nALL TAGS (sorted by text):")
                self.c.execute( "SELECT id, text FROM tags ORDER BY text" )
                for row in self.c:
                    out="{0:>4}{1}: {2}".format(row[0], '*' if row[0] in self.currentTags else ' ', row[1])
                    print(out)
            elif i=="a":
                text=self.getInput("\nTag text (empty to abort): ")
                # TODO: validate input
                if text:
                    try:
                        self.c.execute( "INSERT INTO tags (text) VALUES (?)", (text,) )
                        db.commit()
                        print("Tag added, new ID is", self.c.lastrowid)
                    except sqlite3.Error as e:
                        print("An sqlite3 error occurred:", e.args[0])
                    except Exception as e:
                        print("Error while adding tag: {0}.".format(e.args[0]))

            elif i=="d":
                id=self.getInput("\nID to delete (empty to abort): ")
                if id:
                    try:
                        dellines = self.askYesNo("Also delete all taglines associated with that tag?")

                        id=int(id)
                        if dellines == "y":
                            # delete lines of associated taglines
                            self.db.execute("""DELETE FROM lines WHERE id IN (SELECT
                                l.id FROM lines l JOIN tag t ON t.tagline=l.tagline WHERE t.tag=?)""", (id,))
                            # delete associated taglines
                            self.c.execute( """DELETE FROM taglines WHERE id IN (SELECT
                                tl.id FROM taglines tl JOIN tag t ON t.tagline=tl.id WHERE t.tag=?)""", (id,) )
                            deleted = self.c.rowcount
                            if deleted==1: output = " and one tagline"
                            else: output = " and {0} taglines".format(deleted)
                        else:
                            output = ""
                        self.c.execute( "DELETE FROM tag WHERE tag=?", (id,) )
                        self.c.execute( "DELETE FROM tags WHERE id=?", (id,) )
                        self.db.commit()
                        print("Tag{0} deleted.".format(output))
                    except ValueError:
                        print("Error: no integer ID.")
                    except sqlite3.Error as e:
                        print("An sqlite3 error occurred:", e.args[0])
                    except Exception as e:
                        print("Error while deleting tag: {0}.".format(e.args[0]))

            elif i=="t":
                if type(id) is not int:
                    id=self.getInput("\nID to toggle (empty to abort): ")
                    if id:
                        try:
                            id=int(id)
                        except ValueError:
                            print("Error: no integer ID.")
                if type(id) is int:
                    self.c.execute( "SELECT id, text FROM tags WHERE id=?", (id,) )
                    row = self.c.fetchone()
                    if not row:
                        print("Error: no valid ID.")
                    else:
                        if id in self.currentTags:
                            i=self.currentTags.index(id)
                            self.currentTags=self.currentTags[0:i]+self.currentTags[i+1:]
                            print("Tag '{0}' disabled.".format(row[1]))
                        else:
                            self.currentTags.append(id)
                            print("Tag '{0}' enabled.".format(row[1]))

            elif i=="q":
                return
            elif i=="Q":
                self.exitTaglines()
            else: i="h"

    def taglinesMenu(self): #{{{2
        """The menu with which to alter the actual taglines."""
        i="h"
        while True:
            print()
            if i=="h":
                print("l - list last 5 taglines    L - list all taglines")
                print("a - add new tagline         any number - show tagline of that ID")
                print("e - edit tagline            A - go to author menu")
                print("d - delete tagline          T - go to tag menu")
                print("q - quit menu               Q - quit Taglines")
            i=self.getInput("TAGLINES menu selection: ")

            if i in ("l", "L") or i.isdecimal():
                print()
                q="SELECT t.id, a.name, source, remark, date FROM taglines t LEFT JOIN authors a ON t.author=a.id"
                if i=="l":
                    self.c.execute("SELECT COUNT(id) FROM taglines")
                    r=self.c.fetchone()
                    q+=" ORDER BY t.id LIMIT {0},5".format(max(0,r[0]-5))
                    print("LAST 5 TAGLINES")
                elif i=="L":
                    q+=" ORDER BY t.id"
                    print("ALL TAGLINES")
                elif i.isdecimal():
                    id=int(i)
                    q+=" WHERE t.id='{0}'".format(id)
                else: continue
                sub=self.db.cursor()
                self.c.execute( q )
                anzahl = -1
                for index, r in enumerate(self.c):
                    anzahl = index
                    output=[]
                    if r[1] is not None: output.append("by "+r[1])
                    if r[4] is not None: output.append("from "+r[4].isoformat())
                    if r[2] is not None: output.append("source: "+r[2])
                    if r[3] is not None: output.append("remark: "+r[3])
                    sub.execute( "SELECT text FROM tags JOIN tag t ON t.tagline=? AND t.tag=tags.id ORDER BY text", (r[0],) )
                    tags=sub.fetchall()
                    tags=[t[0] for t in tags]
                    if tags:
                        output.append(str("tags: "+",".join(tags)))
                    print("#{0:>5}{1}".format(
                        r[0], ": "+", ".join(output) if output else ""))
                    sub.execute( "SELECT l.id, l.date, language, text FROM lines l LEFT JOIN taglines t ON l.tagline=t.id WHERE t.id=?", (r[0],) )
                    for t in sub:
                        print("     Line #{0:>5}:{1}{2}: {3}".format(
                            t[0],
                            " ("+t[1].isoformat()+")" if t[1] is not None else "",
                            " lang="+t[2] if t[2] is not None else "",
                            t[3] if t[3] else ""))
                if (anzahl==-1):
                    print("No match found.")
            elif i=="a":
                print("\nADD NEW TAGLINE")
                print("Current author:", end=' ')
                if self.currentAuthor is None: print("None")
                else:
                    self.c.execute( "SELECT name FROM authors WHERE id=?", (self.currentAuthor,) )
                    print(self.c.fetchone()[0])
                print("Current Tags:  ", end=' ')
                if len(self.currentTags)==0: print("None")
                else:
                    tags=",".join([str(t) for t in self.currentTags])
                    self.c.execute( "SELECT text FROM tags WHERE id IN ("+tags+") ORDER BY text" )
                    tags=self.c.fetchall()
                    tags=[t[0] for t in tags]
                    print(", ".join(tags))
                print("Optional information:")
                source=self.getInput("  Source: ")
                remark=self.getInput("  Remark: ")
                when=self.getInput("  Date (yyyy-mm-dd): ")
                # TODO: validate date
                texts=[]

                while True:
                    print("\n  ADD ITEMS TO TAGLINE")
                    print("  a - add an item            w - done, save lines to database")
                    print("  m - manage entered items   q - quit to previous menu, discarding changes")
                    i=self.getInput("  ")

                    if i=="q":
                        break
                    elif i=="a":
                        print("    ENTER A NEW ITEM")
                        language=self.getInput("    Language (ISO code): ")
                        print("    Text (f=finish, r=restart, c=correct last line, a=abort):")
                        print("".join(["         {0}".format(x) for x in range(1,9)]))
                        print("1234567890"*8)
                        lines=[]
                        while True:
                            line=self.getInput()
                            if line=="r":
                                lines=[]
                                print("--> Input restarted.")
                            elif line=="c":
                                lines=lines[:-1]
                                print("--> Last line deleted.")
                            elif line=="f":
                                texts.append((language, "\n".join(lines).strip()))
                                break
                            # special case for importing from a text file via copy+paste more easily
                            elif line=="---":
                                texts.append(("de", "\n".join(lines).strip()))
                                language="en"
                                lines=[]
                            elif line=="a": break
                            else: lines.append(line)
                    elif i=="m":
                        for lang, text in texts:
                            print("\nLanguage: {0}\n{1}".format(lang, text))
                        lang = self.getInput("\n   Language to delete (empty to do nothing): ")
                        for number, item in enumerate(texts):
                            if item[0] == lang:
                                texts.pop(number)
                                print("Item with language '{0}' deleted.".format(item[0]))
                                break
                    if i=="w":
                        self.c.execute("INSERT INTO taglines (author,source,remark,date) values (?,?,?,?)", (
                            self.currentAuthor if self.currentAuthor else None,
                            source if source!="" else None,
                            remark if remark!="" else None,
                            when if when!="" else None))
                        id=self.c.lastrowid
                        for line in texts:
                            self.c.execute("INSERT INTO lines (tagline, date, language, text) values (?,?,?,?)", (
                                id,
                                date.today().isoformat(),
                                line[0] if line[0]!='' else None,
                                line[1] if line[1]!='' else None))
                        for t in self.currentTags:
                            self.c.execute("INSERT INTO tag (tag, tagline) values (?,?)", (
                                t, id))
                        self.db.commit()
                    if i=="w"or i=="q": break

            elif i=="e":
                print("TODO")
            elif i=="d":
                id=self.getInput("\nID to delete (empty to abort): ")
                if id!="":
                    try:
                        id=int(id)
                        self.c.execute("SELECT id FROM taglines WHERE id=?", (id,) )
                        if self.c.fetchone():
                            self.c.execute( 'DELETE FROM taglines WHERE id=?', (id,) )
                            self.c.execute( "DELETE FROM tag WHERE tagline=?", (id,) )
                            self.c.execute( "DELETE FROM lines WHERE tagline=?", (id,) )
                            self.db.commit()
                        print("Tagline and all assiciated entires deleted.")
                    except ValueError:
                        print("Error: no integer ID.")
                    except:
                        print("Error while deleting tagline.")

            elif i=="A":
                self.authorMenu()
            elif i=="T":
                self.tagMenu()
            elif i=="q":
                break
            elif i=="Q":
                self.exitTaglines()
            else: i="h"

    def mainMenu(self): #{{{2
        while True:
            print("\nBy your command...")
            print("a - Author menu")
            print("t - Tag menu")
            print("l - taglines menu")
            print("h - show key help (available in every menu)")
            print("q - quit         Q - quit Taglines (in all submenus)")
            i=self.getInput("MAIN menu selection: ")
            if i=="a":
                self.authorMenu()
            elif i=="t":
                self.tagMenu()
            elif i=="l":
                self.taglinesMenu()
            elif i=="q":
                self.exitTaglines()
            elif i=="Q":
                self.exitTaglines()
        #}}}2
    #}}}1


if args.interactive:
    shellmode = CShellmode()
    shellmode.mainMenu()
    exit(0)
