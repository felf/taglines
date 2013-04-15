import taglines
import sys

class ShellUI: #{{{1 interactive mode
    """ Shellmode class

    It provides a hierarchy of menus which are used to inspect
    and modify the content of the database."""

    def __init__(self, db): #{{{1
        self.currentAuthor=None
        self.currentTags=[]
        self.db = db
        self.db.open()

    def colorstring(self, color): # {{{1
        """ Return terminal escape sequences for colourful output. """
        _colors = {
            'black':  '30',
            'red':    '31',
            'green':  '32',
            'yellow': '33',
            'blue':   '34',
            'purple': '35',
            'cyan':   '36',
            'white':  '37'
        }
        return "\033[{0};{1}m".format(
                "0" if color[0].islower() else "1",
                _colors.get(color.lower(), "0"))

    def print(self, what, newline = True): # {{{1
        """ Print a string or a list of coloured strings. """
        ending = "\n" if newline else ""
        if type(what) is str:
            print(what, end = ending)
        else:
            o = ""
            for part in what:
                o += "".join([
                    self.colorstring(part[0]) + part[1] + "\033[0;0m"
                        if type(part) is tuple else part
                    ]) + "\033[0;0m"
            print(o, end = ending)

    def menu(self, breadcrumbs, choices, prompt = "", silent = False, allowInts = False):
        if not silent:
            length = 10
            self.print([("White", "\n Taglines: ")], False)
            for level, crumb in enumerate(breadcrumbs):
                if level>0:
                    print(" > ", end="")
                    length += 3
                self.print([("White", crumb.upper())], False)
                length += len(crumb)
            print("\n" + "-" * (length+2), end="\n\n")

        keys = [False]
        for choice in choices:
            key, text = choice.split(" - ", 1)
            if key: keys.append(key.lstrip()[0])
            if not silent:
                self.print([("Yellow", key), " - "+text if key else text], False)

        """ main menu """
        if len(breadcrumbs) == 1:
            print("\nAlso available in all menus:")
            for choice in ["   q / ^d - quit to parent menu   ", "Q / ^c - quit program   ", "h - show menu help"]:
                key, text = choice.split(" - ")
                self.print([("Yellow", key), " - "+text], False)
            print("")

        keys.extend(["h", "q"])
        while True:
            if not prompt: prompt = breadcrumbs[-1] + " menu choice: "
            i = self.getInput("\n"+prompt)
            if i == "": continue
            elif i=="Q":
                self.exitTaglines()
            elif i in keys: return i
            elif allowInts and i.isdecimal(): return int(i)
            self.print([("Red", "Invalid choice.")])


    def getInput(self, text="", nonempty=False): #{{{1
        """ This is a common function to get input and catch Ctrl+C/D. """
        while True:
            try:
                self.print([("green", text)], False)
                i = input()
                if nonempty and not i:
                    print("Empty string not allowed here.")
                else:
                    return i
            # Ctrl+C
            except KeyboardInterrupt:
                self.exitTaglines()
            # Ctrl+D
            except EOFError:
                print()
                return False

    def askYesNo(self, text, default = "n"): #{{{1
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

    def exitTaglines(self): #{{{1
        try:
            # not using askYesNo b/c of own handling of Ctrl+C/D
            ok=input("\nReally quit Taglines?  [y/N] ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if ok and "yes".startswith(ok.lower()):
            print("bye")
            sys.exit();

    def authorMenu(self, breadcrumbs): #{{{1
        """The menu with which to alter author information."""

        choice = "h"
        while True:
            choice = self.menu(breadcrumbs+["Author"],
                   ["a - add author      ", "l - list all authors\n",
                    "d - delete author   ", "c - set current author for new taglines\n"],
                    silent = choice != "h")

            if not choice or choice=="q": return
            elif choice=="l":
                print("\nALL AUTHORS (sorted by name):")
                c = self.db.execute( "SELECT id, name, born, died FROM authors ORDER BY name" )
                for row in c:
                    out="{0:>4}{1}: {2}".format(row[0], '*' if self.currentAuthor==row[0] else ' ', row[1])
                    if row[2] is not None or row[3] is not None:
                        out+=" ("+str(row[2])+"-"+str(row[3])+")"
                    print(out)
            elif choice=="a":
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
                        c = self.db.execute( "INSERT INTO authors (name, born, died) VALUES (?,?,?)", (
                            name, born, died), True )
                        print("Author added, new ID is {0}".format(c.lastrowid))
                    except sqlite3.Error as e:
                        print("An sqlite3 error occurred:", e.args[0])
                    except Exception as e:
                        print("Error while adding author:", e.args[0])

            elif choice=="d":
                id=self.getInput("\nID to delete (empty to abort): ")
                if id:
                    try:
                        id=int(id)
                        self.db.execute( 'DELETE FROM authors WHERE id=?', (id,), True )
                        print("Author deleted.")
                    except ValueError:
                        print("Error: no integer ID.")
                    except Exception as e:
                        print("Error while deleting author: {0}.".format(e.args[0],))
            elif choice=="c":
                id=self.getInput("\nID of new current author (empty to abort, 'u' to unset): ")
                if id:
                    if id=="u":
                        self.currentAuthor=None
                    else:
                        try:
                            c = self.db.execute("SELECT id FROM authors WHERE id=?", (id,))
                            if c.fetchone() is None:
                                print("Error: no valid ID.")
                            else:
                                self.currentAuthor=int(id)
                        except ValueError:
                            print("Error: no integer ID.")

    def tagMenu(self): #{{{1
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

            if not i or i=="q": return
            elif i=="l":
                print("\nALL TAGS (sorted by text):")
                c = self.db.execute( "SELECT id, text FROM tags ORDER BY text" )
                for row in c:
                    out="{0:>4}{1}: {2}".format(row[0], '*' if row[0] in self.currentTags else ' ', row[1])
                    print(out)
            elif i=="a":
                text=self.getInput("\nTag text (empty to abort): ")
                # TODO: validate input
                if text:
                    try:
                        c = self.db.execute( "INSERT INTO tags (text) VALUES (?)", (text,), True)
                        print("Tag added, new ID is", c.lastrowid)
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
                            c = self.db.execute( """DELETE FROM taglines WHERE id IN (SELECT
                                tl.id FROM taglines tl JOIN tag t ON t.tagline=tl.id WHERE t.tag=?)""", (id,) )
                            deleted = c.rowcount
                            if deleted==1: output = " and one tagline"
                            else: output = " and {0} taglines".format(deleted)
                        else:
                            output = ""
                        self.db.execute( "DELETE FROM tag WHERE tag=?", (id,) )
                        self.db.execute( "DELETE FROM tags WHERE id=?", (id,), True)
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
                    c = self.db.execute( "SELECT id, text FROM tags WHERE id=?", (id,) )
                    row = c.fetchone()
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

            elif i=="Q":
                self.exitTaglines()
            else: i="h"

    def taglinesMenu(self): #{{{1
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

            if not i or i=="q": return
            elif i in ("l", "L") or i.isdecimal():
                print()
                q="SELECT t.id, a.name, source, remark, date FROM taglines t LEFT JOIN authors a ON t.author=a.id"
                if i=="l":
                    c = self.db.execute("SELECT COUNT(id) FROM taglines")
                    r = c.fetchone()
                    q+=" ORDER BY t.id LIMIT {0},5".format(max(0,r[0]-5))
                    print("LAST 5 TAGLINES")
                elif i=="L":
                    q+=" ORDER BY t.id"
                    print("ALL TAGLINES")
                elif i.isdecimal():
                    id=int(i)
                    q+=" WHERE t.id='{0}'".format(id)
                else: continue
                c = self.db.execute( q )
                anzahl = -1
                for index, r in enumerate(c):
                    anzahl = index
                    output=[]
                    if r[1] is not None: output.append("by "+r[1])
                    if r[4] is not None: output.append("from "+r[4].isoformat())
                    if r[2] is not None: output.append("source: "+r[2])
                    if r[3] is not None: output.append("remark: "+r[3])
                    sub = self.db.execute( "SELECT text FROM tags JOIN tag t ON t.tagline=? AND t.tag=tags.id ORDER BY text", (r[0],) )
                    tags=sub.fetchall()
                    tags=[t[0] for t in tags]
                    if tags:
                        output.append(str("tags: "+",".join(tags)))
                    print("#{0:>5}{1}".format(
                        r[0], ": "+", ".join(output) if output else ""))
                    sub = self.db.execute( "SELECT l.id, l.date, language, text FROM lines l LEFT JOIN taglines t ON l.tagline=t.id WHERE t.id=?", (r[0],) )
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
                    c = self.db.execute( "SELECT name FROM authors WHERE id=?", (self.currentAuthor,) )
                    print(c.fetchone()[0])
                print("Current Tags:  ", end=' ')
                if len(self.currentTags)==0: print("None")
                else:
                    tags=",".join([str(t) for t in self.currentTags])
                    c = self.db.execute( "SELECT text FROM tags WHERE id IN ("+tags+") ORDER BY text" )
                    tags=c.fetchall()
                    tags=[t[0] for t in tags]
                    print(", ".join(tags))
                print("Optional information:")
                source=self.getInput("  Source: ")
                remark=self.getInput("  Remark: ")
                when=self.getInput("  Date (yyyy-mm-dd): ")
                # TODO: validate date
                texts={}

                while True:
                    print("\n  ADD ITEMS TO TAGLINE")
                    print("  a - add an item            w - done, save lines to database")
                    print("  m - manage entered items   q - quit to previous menu, discarding changes")
                    i=self.getInput("  ")

                    if i=="a":
                        print("    ENTER A NEW ITEM")
                        language = self.getInput("    Language (ISO code): ", nonempty = True)
                        if not language: continue
                        if texts.get(language):
                            if self.askYesNo("    There is already an item with this language. Overwrite it?") == "n":
                                continue
                        print("    Text ('r'=restart, 'c'=correct last line, 'a'=abort, 'f' or two empty lines=finish:")
                        print("".join(["         {0}".format(x) for x in range(1,9)]))
                        print("1234567890"*8)
                        lines=[]
                        while True:
                            line=self.getInput()
                            if line=="r":
                                lines=[]
                                print("--> Input restarted.")
                            elif line=="c":
                                if lines:
                                    lines.pop()
                                print("--> Last line deleted.")
                            elif line=="f" or line=="" and len(lines)>0 and lines[-1]=="":
                                texts[language] = "\n".join(lines).strip()
                                break
                            # special case for importing from a text file via copy+paste more easily
                            elif line=="---":
                                texts["de"] = "\n".join(lines).strip()
                                language="en"
                                lines=[]
                            elif line=="a": break
                            else: lines.append(line)
                    elif i=="m":
                        for lang, text in texts.items():
                            print("\nLanguage: {0}\n{1}".format(lang, text))
                        lang = self.getInput("\n   Language to delete (empty to do nothing): ")
                        if texts.pop(lang, None):
                            print("Item with language '{0}' deleted.".format(lang))
                    elif i=="w":
                        c = self.db.execute("INSERT INTO taglines (author,source,remark,date) values (?,?,?,?)", (
                            self.currentAuthor if self.currentAuthor else None,
                            source if source!="" else None,
                            remark if remark!="" else None,
                            when if when!="" else None), commit = True)
                        id = c.lastrowid
                        for lang, text in texts.items():
                            self.db.execute("INSERT INTO lines (tagline, date, language, text) values (?,?,?,?)",
                                    (id, date.today().isoformat(), lang, text))
                        for t in self.currentTags:
                            self.db.execute("INSERT INTO tag (tag, tagline) values (?,?)", (t, id))
                        self.db.commit()
                        break
                    elif i=="q":
                        if texts:
                            if self.askYesNo("    This will discard your changes. Continue?", "n") == "y":
                                break

            elif i=="e":
                print("TODO")
            elif i=="d":
                id=self.getInput("\nID to delete (empty to abort): ")
                if id!="":
                    try:
                        id=int(id)
                        c = self.db.execute("SELECT id FROM taglines WHERE id=?", (id,) )
                        if c.fetchone():
                            c.execute( 'DELETE FROM taglines WHERE id=?', (id,) )
                            c.execute( "DELETE FROM tag WHERE tagline=?", (id,) )
                            c.execute( "DELETE FROM lines WHERE tagline=?", (id,), commit = True )
                        print("Tagline and all assiciated entires deleted.")
                    except ValueError:
                        print("Error: no integer ID.")
                    except:
                        print("Error while deleting tagline.")

            elif i=="A":
                self.authorMenu()
            elif i=="T":
                self.tagMenu()
            elif i=="Q":
                self.exitTaglines()
            else: i="h"

    def mainMenu(self): #{{{1
        while True:
            bc = ["Main"]
            choice = self.menu(bc,
                    ["   a - Author menu    ", "t - Tag menu    ", "l - taglines menu"],
                    "By your command: ")
            if choice==False or choice=="q" or choice=="Q":
                self.exitTaglines()
            if choice=="a":
                self.authorMenu(bc)
            elif choice=="t":
                self.tagMenu()
            elif choice=="l":
                self.taglinesMenu()
        #}}}2
    #}}}1
