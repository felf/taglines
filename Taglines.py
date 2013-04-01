#!/usr/bin/python2
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
import string
#}}}1

# create a new sqlite database file {{{1
# ----------------------------------------------------------------
def db_initialise_file():
    """Initialises a new, empty database"""
    try:
        dbfile=open( args.file, 'w' )
        dbfile.close()
        print "Creating new database file...",
        db=sqlite3.connect( args.file )
        #db.text_factory=str
        db.execute('CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT, born INT DEFAULT NULL, died INT DEFAULT NULL);')
        db.execute('CREATE TABLE lines (id INTEGER PRIMARY KEY, tagline INT, date DATE, language VARCHAR(5), text TEXT);')
        db.execute('CREATE TABLE tag (id INTEGER PRIMARY KEY, tag INT, tagline INT);')
        db.execute('CREATE TABLE taglines (id INTEGER PRIMARY KEY, author INT, source TEXT DEFAULT NULL, remark TEXT DEFAULT NULL, date DATE DEFAULT NULL);')
        db.execute('CREATE TABLE tags (id INTEGER PRIMARY KEY, text TEXT UNIQUE);')
        db.commit()
        c.close()
        print "done."
    except IOError as (errno, strerror):
        print >> sys.stderr, "\nError while creating the database file: "+strerror+". Exiting."
        exit(1)
    except sqlite3.Error, e:
        print "An sqlite3 error occurred:", e.args[0]
    except:
        print >> sys.stderr, "\nError while initialising the database file: "+strerror+". Exiting."
        exit(1)

if args.init:
    if fileexists:
        ok = raw_input("Warning: "+args.file+" already exists. Overwrite? [y/N] ")
        if ok in ('y', 'ye', 'yes'):
            try:
                os.remove( args.file )
            except:
                print >> sys.stderr, "Error: could not delete old file. Exiting."
                exit(1)
        else:
            print "good bye"
            exit(1)
    db_initialise_file()
    exit(0)


# get database handle from file {{{1
# ----------------------------------------------------------------
def get_database_from_file(path):
    if path is None:
        print >> sys.stderr, "Error: no path to database given. Exiting."
        exit(1)

    args.file=os.path.abspath( path )
    fileexists=os.path.exists( path )
    validfile=os.path.isfile( path ) if fileexists else True

    if not validfile:
        print >> sys.stderr, "Error: the given path is not a valid file. Exiting."
        exit(1)

    if not fileexists and not args.init:
        print >> sys.stderr, "Error: the given file does not exist. Exiting."
        exit(1)

    try:
        db=sqlite3.connect(path, detect_types=True)
        return db
    except:
        print >> sys.stderr, "Error: could not open database file. Exiting."
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
            tagquery="SELECT t1.tagline FROM tag t1 JOIN tags s1 ON t1.tag=s1.id WHERE ("+string.join(
                ["s1.text=?"]*len(args.tag)," OR ")+")"
        else:
            qwhere=["t{0}='{1}'".format(x,args.tag[x]) for x in range(len(args.tag))]
            tagquery="SELECT t1.tagline FROM "+string.join(
                ["tag t{0}, tags s{0} on s{0}.id=t{0}.tag AND s{0}.text=? AND t1.tagline=t{0}.tagline".format(x+1,args.tag[x]) for x in range(len(args.tag))], ' JOIN ')
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
            print "%"
        print r[0].encode("utf-8")
    exit(0)


# stand-alone DB functions {{{1
# ----------------------------------------------------------------
if args.show_tags:
    db = get_database_from_file(args.file);
    for row in db.execute( "SELECT text FROM tags ORDER BY text" ):
        print row[0]
    exit(0)


if args.show_authors:
    db = get_database_from_file(args.file);
    for row in db.execute( "SELECT name, born, died FROM authors ORDER BY name" ):
        out=row[0]
        if row[1] is not None or row[2] is not None:
            out+=" ("+str(row[1])+"-"+str(row[2])+")"
        print out
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

    print "Number of taglines:        %6d" % taglinesnumber
    print "Number of texts:           %6d   (ø %5.2f per tagline)" % (
        linesnumber, float(linesnumber)/taglinesnumber)
    print "Average text length:       %8.1f" % (float(length)/linesnumber)
    print "Number of tags:            %6d" % tagsnumber
    print "Number of tag assignments: %6d   (ø %5.2f per tagline)" % (
        tagnumber, float(tagnumber)/taglinesnumber)
    print "Number of authors:         %6d" % authorsnumber
    print "Used languages:            %6d" % languages
    exit(0)


class CShellmode: #{{{1
    """ Shellmode class

    It provides a hierarchy of menus which are used to inspect
    and modify the content of the database."""

    def __init__(self):
        self.currentAuthor=None
        self.currentTags=[]
        self.db = get_database_from_file(args.file)
        self.c = self.db.cursor()

    def exitTaglines(self):
        ok=raw_input("\nReally quit Taglines?  [y/N] ")
        if ok!='' and 'yes'.startswith(ok.lower()):
            print "bye"
            sys.exit();

    def authorMenu(self): #{{{2
        """The menu with which to alter author information."""
        i="h"
        while True:
            print
            if i=="h":
                print "a - add author       l - list all authors"
                print "d - delete author    c - set current author for new taglines"
                print "h - help"
                print "q - quit menu        Q - quit Taglines"
            i=raw_input("AUTHOR menu selection: ")

            if i=="l":
                print "\nALL AUTHORS (sorted by name):"
                self.c.execute( "SELECT id, name, born, died FROM authors ORDER BY name" )
                for row in self.c:
                    out="{0:>4}{1}: {2}".format(row[0], '*' if self.currentAuthor==row[0] else ' ', row[1].encode("utf-8"))
                    if row[2] is not None or row[3] is not None:
                        out+=" ("+str(row[2])+"-"+str(row[3])+")"
                    print out
            elif i=="a":
                name=raw_input("\nName (empty to abort): ")
                # TODO: validate input
                if name!="":
                    try:
                        born=int(raw_input("Year of birth: "))
                    except ValueError:
                        born=None
                    try:
                        died=int(raw_input("Year of death: "))
                    except ValueError:
                        died=None
                    try:
                        self.c.execute( "INSERT INTO authors (name, born, died) VALUES (?,?,?)", (
                            unicode(name, "utf-8"), born, died) )
                        self.db.commit()
                        print "Author added, new ID is {0}".format(self.c.lastrowid)
                    except sqlite3.Error, e:
                        print "An sqlite3 error occurred:", e.args[0]
                    except Exception, e:
                        print "Error while adding author:", e.args[0]

            elif i=="d":
                id=raw_input("\nID to delete (empty to abort): ")
                if id!="":
                    try:
                        id=int(id)
                        self.c.execute( 'DELETE FROM authors WHERE id=?', (id,) )
                        db.commit()
                        print "Author deleted."
                    except ValueError:
                        print "Error: no integer ID."
                    except:
                        print "Error while deleting author."
            elif i=="c":
                id=raw_input("\nID of new current author (empty to abort, 'u' to unset): ")
                if id!="":
                    if id=="u":
                        self.currentAuthor=None
                    else:
                        try:
                            self.c.execute("SELECT id FROM authors WHERE id=?", (id,))
                            if self.c.fetchone() is None:
                                print "Error: no valid ID."
                            else:
                                self.currentAuthor=int(id)
                        except ValueError:
                            print "Error: no integer ID."
            elif i=="q":
                return
            elif i=="Q":
                self.exitTaglines()
            else: i="h"

    def tagMenu(self): #{{{2
        """The menu with which to alter tag information."""
        i="h"
        while True:
            print
            if i=="h":
                print "a - add tag       l - list all tags"
                print "d - delete tag    t - toggle tag (or simply enter the ID)"
                print "h - help"
                print "q - quit menu     Q - quit Taglines"
            i=raw_input("TAGS menu selection: ")

            # Abkürzung: statt "t" und dann ID eingeben einfach nur die ID
            try:
                id=int(i)
            except ValueError:
                id=None
            if type(id) is int:
                i="t"

            if i=="l":
                print "\nALL TAGS (sorted by text):"
                self.c.execute( "SELECT id, text FROM tags ORDER BY text" )
                for row in self.c:
                    out="{0:>4}{1}: {2}".format(row[0], '*' if row[0] in self.currentTags else ' ', row[1])
                    print out
            elif i=="a":
                text=raw_input("\nText (empty to abort): ")
                # TODO: validate input
                if text!="":
                    try:
                        self.c.execute( "INSERT INTO tags (text) VALUES (?)", (text,) )
                        db.commit()
                        print "Tag added, new ID is {0}".format(self.c.lastrowid)
                    except sqlite3.Error, e:
                        print "An sqlite3 error occurred:", e.args[0]
                    except:
                        print "Error while adding tag."

            elif i=="d":
                id=raw_input("\nID to delete (empty to abort): ")
                if id!="":
                    try:
                        id=int(id)
                        self.c.execute( "DELETE FROM tags WHERE id=?", (id,) )
                        db.commit()
                        print "Tag deleted."
                    except ValueError:
                        print "Error: no integer ID."
                    except sqlite3.Error, e:
                        print "An sqlite3 error occurred:", e.args[0]
                    except:
                        print "Error while deleting tag."

            elif i=="t":
                if type(id) is not int:
                    id=raw_input("\nID to toggle (empty to abort): ")
                    if id!="":
                        try:
                            id=int(id)
                        except ValueError:
                            print "Error: no integer ID."
                if type(id) is int:
                    self.c.execute( "SELECT id FROM tags WHERE id=?", (id,) )
                    if self.c.fetchone()==None:
                        print "Error: no valid ID."
                    else:
                        if id in self.currentTags:
                            i=self.currentTags.index(id)
                            self.currentTags=self.currentTags[0:i]+self.currentTags[i+1:]
                            print "Tag disabled."
                        else:
                            self.currentTags.append(id)
                            print "Tag enabled."

            elif i=="q":
                return
            elif i=="Q":
                self.exitTaglines()
            else: i="h"

    def taglinesMenu(self): #{{{2
        """The menu with which to alter the actual taglines."""
        i="h"
        while True:
            print
            if i=="h":
                print "l - list last 5 taglines    L - list all taglines"
                print "a - add new tagline         A - go to author menu"
                print "e - edit tagline            T - go to tag menu"
                print "d - delete tagline"
                print "q - quit menu               Q - quit Taglines"
            i=raw_input("TAGLINES menu selection: ")
            if i=="l" or i=="L":
                print
                q="SELECT t.id, a.name, source, remark, date FROM taglines t LEFT JOIN authors a ON t.author=a.id ORDER BY t.id"
                if i=="l":
                    self.c.execute("SELECT COUNT(id) FROM taglines")
                    r=self.c.fetchone()
                    q+=" LIMIT {0},5".format(max(0,r[0]-5))
                    print "ALL ",
                print "TAGLINES"
                sub=self.db.cursor()
                self.c.execute( q )
                for r in self.c:
                    output=[]
                    if r[1] is not None: output.append("by "+r[1])
                    if r[4] is not None: output.append("from "+r[4].isoformat())
                    if r[2] is not None: output.append("source: "+r[2])
                    if r[3] is not None: output.append("remark: "+r[3])
                    sub.execute( "SELECT text FROM tags JOIN tag t ON t.tagline=? AND t.tag=tags.id ORDER BY text", (r[0],) )
                    tags=sub.fetchall()
                    tags=[t[0] for t in tags]
                    if tags:
                        output.append("tags: "+string.join(tags, ','))
                    print "#{0:>5}{1}".format(
                        r[0], ": "+string.join(output,', ').encode("utf-8") if output else "")
                    sub.execute( "SELECT l.id, l.date, language, text FROM lines l LEFT JOIN taglines t ON l.tagline=t.id WHERE t.id=?", (r[0],) )
                    for t in sub:
                        print "     Line #{0:>5}:{1}{2}: {3}".format(
                            t[0],
                            " ("+t[1].isoformat()+")" if t[1] is not None else "",
                            " lang="+t[2].encode("utf-8") if t[2] is not None else "",
                            t[3].encode("utf-8") if t[3] else "")
            elif i=="a":
                print "\nADD NEW TAGLINE"
                print "Current author:",
                if self.currentAuthor is None: print "None"
                else:
                    self.c.execute( "SELECT name FROM authors WHERE id=?", (self.currentAuthor,) )
                    print self.c.fetchone()[0].encode("utf-8")
                print "Current Tags:  ",
                if len(self.currentTags)==0: print "None"
                else:
                    tags=string.join([str(t) for t in self.currentTags],',')
                    self.c.execute( "SELECT text FROM tags WHERE id IN ("+tags+") ORDER BY text" )
                    tags=self.c.fetchall()
                    tags=[t[0] for t in tags]
                    print string.join(tags, ', ')
                print "Optional information:"
                source=raw_input("  Source: ")
                remark=raw_input("  Remark: ")
                when=raw_input("  Date (yyyy-mm-dd): ")
                # TODO: validate date
                texts=[]

                while True:
                    print "\n  ADD ITEMS TO TAGLINE"
                    print "  a - add an item       w - done, save lines to database"
                    print "  d - delete an item    q - quit to previous menu, discarding changes"
                    i=raw_input("  ")
                    if i=="q":
                        break
                    elif i=="a":
                        print "    ENTER A NEW ITEM"
                        language=raw_input("    Language (ISO code): ")
                        print "    Text (f=finish, r=restart, c=correct last line, a=abort):"
                        lines=[]
                        while True:
                            line=raw_input()
                            if line=="r":
                                lines=[]
                                print "--> Input restarted."
                            elif line=="c":
                                lines=lines[:-1]
                                print "--> Last line deleted."
                            elif line=="f":
                                texts.append((language, string.join(lines,"\n")))
                                break
                            elif line=="---":
                                texts.append(("de", string.join(lines,"\n")))
                                language="en"
                                lines=[]
                            elif line=="a": break
                            else: lines.append(line)
                    elif i=="d":
                        print "TODO"
                    if i=="w":
                        self.c.execute("INSERT INTO taglines (author,source,remark,date) values (?,?,?,?)", (
                            self.currentAuthor if self.currentAuthor else None,
                            unicode(source,"utf-8") if source!="" else None,
                            unicode(remark,"utf-8") if remark!="" else None,
                            when if when!="" else None))
                        id=self.c.lastrowid
                        for line in texts:
                            self.c.execute("INSERT INTO lines (tagline, date, language, text) values (?,?,?,?)", (
                                id,
                                date.today().isoformat(),
                                unicode(line[0],"utf-8") if line[0]!='' else None,
                                unicode(line[1],"utf-8") if line[1]!='' else None))
                        for t in self.currentTags:
                            self.c.execute("INSERT INTO tag (tag, tagline) values (?,?)", (
                                t, id))
                        self.db.commit()
                    if i=="w"or i=="q": break

            elif i=="e":
                print "TODO"
            elif i=="d":
                id=raw_input("\nID to delete (empty to abort): ")
                if id!="":
                    try:
                        id=int(id)
                        self.c.execute("SELECT id FROM taglines WHERE id=?", (id,) )
                        if self.c.fetchone():
                            self.c.execute( 'DELETE FROM taglines WHERE id=?', (id,) )
                            self.c.execute( "DELETE FROM tag WHERE tagline=?", (id,) )
                            self.c.execute( "DELETE FROM lines WHERE tagline=?", (id,) )
                            self.db.commit()
                        print "Tagline and all assiciated entires deleted."
                    except ValueError:
                        print "Error: no integer ID."
                    except:
                        print "Error while deleting tagline."

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
        print "\nBy your command..."
        while True:
            print "a - Author menu"
            print "t - Tag menu"
            print "l - taglines menu"
            print "h - show key help (available in every menu)"
            print "q - quit         Q - quit Taglines (in all submenus)"
            i=raw_input("MAIN menu selection: ")
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
