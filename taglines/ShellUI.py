# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
import taglines
import sqlite3
import sys
from datetime import date

if sys.version_info.major == 2:
    input = raw_input


class ShellUI:  # {{{1 interactive mode
    """ Shellmode class

    It provides a hierarchy of menus which are used to inspect
    and modify the content of the database."""


    class ExitShellUI(Exception):  # {{{1
        """ Exception that is raised to leave the menu hierarchy. """

        def __init__(self):
            Exception()


    def __init__(self, db):  # {{{1
        self.currentAuthor = None
        self.currentTags = []
        self.db = db
        self.db.open()

    def colorstring(self, color):  # {{{1
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
        return "\033[{};{}m".format(
            "0" if color[0].islower() else "1",
            _colors.get(color.lower(), "0"))

    def print(self, what, newline=True):  # {{{1
        """ Print a string or a list of coloured strings. """
        ending = "\n" if newline else ""
        if type(what) is str:
            print(what, end=ending)
        else:
            if type(what) is tuple:
                what = [what]
            o = ""
            for part in what:
                o += "".join([
                    self.colorstring(part[0]) + part[1] + "\033[0;0m"
                        if type(part) is tuple else part
                    ]) + "\033[0;0m"
            print(o, end=ending)

    def printWarning(self, what):  # {{{1
        """ Convenience function to print a red warning message. """
        self.print(("Red", what))

    def menu(self, breadcrumbs, choices=None, prompt="", silent=False, noHeader=False, allowInt=False):  # {{{1
        if not (silent or noHeader):
            length = 10
            self.print(("White", "\n Taglines: "), False)
            for level, crumb in enumerate(breadcrumbs):
                if level > 0:
                    print(" > ", end="")
                    length += 3
                self.print(("White", crumb.upper()), False)
                length += len(crumb)
            print("\n" + "-" * (length+2), end="\n\n")
        # no choices given -> just output the headline
        if not choices:
            return

        keys = [False]
        for choice in choices:
            key, text = choice.split(" - ", 1)
            if key:
                keys.append(key.lstrip()[0])
            if not silent:
                self.print([("Yellow", key), " - "+text if key else text], False)

        """ main menu """
        if len(breadcrumbs) == 1:
            print("\nAlso available in all menus:")
            for choice in ["   q/^d - quit to parent menu   ", "Q/^c - quit program   ", "h/? - show menu help"]:
                key, text = choice.split(" - ")
                self.print([("Yellow", key), " - "+text], False)
            print("")

        keys.extend(["h", "?", "q"])
        while True:
            if not prompt:
                prompt = breadcrumbs[-1] + " menu choice: "
            try:
                i = self.getInput("\n"+prompt, allowInt)
            except KeyboardInterrupt:
                i = "Q"

            if i is False:
                return "q"
            elif i == "?":
                return "h"
            elif i == "Q":
                self.exitTaglines()
                continue
            elif i == "":
                continue
            elif i in keys:
                return i
            elif allowInt and type(i) is int:
                return i
            self.printWarning("Invalid choice.")

    def getInput(self, text="", allowEmpty=True, allowInt=False):  # {{{1
        """ This is a common function to get input and catch Ctrl+C/D. """
        while True:
            try:
                self.print(("green", text), False)
                i = input()
                if not allowEmpty and not i:
                    print("Empty string not allowed here.")
                else:
                    if sys.version_info.major == 2:
                        i = i.decode("utf-8")
                    if allowInt:
                        try:
                            i = int(i)
                            return i
                        except ValueError:
                            pass
                    return i
            # Ctrl+C
            except KeyboardInterrupt:
                print()
                self.exitTaglines()
            # Ctrl+D
            except EOFError:
                print()
                return False

    def askYesNo(self, text, default="n", allowCancel=False):  # {{{1
        """ Ask a yes/no question, digest the answer and return the answer.

        default should be either "y" or "n" to set the relevant answer. """

        suffix = ["Y" if default == "y" else "y",
                  "N" if default == "n" else "n"]
        if allowCancel:
            suffix.append("^d")
        text += "  [" + "/".join(suffix) + "] "

        while True:
            i = self.getInput(text)
            if not i:
                if i is False and allowCancel:
                    return False
                i = default
            if i:
                if "yes".startswith(i.lower()):
                    i = "y"
                elif "no".startswith(i.lower()):
                    i = "n"
                else:
                    i = ""
            if i == "":
                print("Please answer yes or no.")
            else:
                return i

    def exitTaglines(self):  # {{{1
        try:
            # not using askYesNo b/c of own handling of Ctrl+C/D
            ok = input("\nReally quit Taglines?  [y/N] ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if ok and "yes".startswith(ok.lower()):
            raise self.ExitShellUI()

    def authorMenu(self, breadcrumbs):  # {{{1
        """The menu with which to alter author information."""

        breadcrumbs = breadcrumbs[:]+["Author"]
        choice = "h"
        while True:
            choice = self.menu(
                breadcrumbs,
                ["a - add author      ", "l - list all authors\n",
                 "d - delete author   ", "c - set current author for new taglines\n"],
                silent=choice != "h", allowInt=True)

            if type(choice) is int:
                author_id = choice
                choice = "c"
            else:
                author_id = None

            if choice == "q":
                return
            elif choice == "l":
                print("\nALL AUTHORS (sorted by name):")
                c = self.db.execute("SELECT id, name, born, died FROM authors ORDER BY name")
                for row in c:
                    out = "{:>4}{}: {}".format(row[0], self.colorstring("Yellow")+"*\033[0;0m" if self.currentAuthor == row[0] else ' ', row[1])
                    if row[2] is not None or row[3] is not None:
                        out += " ("+str(row[2])+"-"+str(row[3])+")"
                    print(out)

            elif choice == "a":
                name = self.getInput("\nName (empty to abort): ")
                # TODO: validate input
                if name != False and name != "":
                    try:
                        born = self.getInput("Year of birth: ")
                        if born == False:
                            continue
                        else:
                            born = int(born)
                    except ValueError:
                        born = None
                    try:
                        died = self.getInput("Year of death: ")
                        if died == False:
                            continue
                        else:
                            died = int(died)
                    except ValueError:
                        died = None
                    try:
                        c = self.db.execute("INSERT INTO authors (name, born, died) VALUES (?,?,?)", (
                            name, born, died), True)
                        print("Author added, new ID is {}".format(c.lastrowid))
                    except sqlite3.Error as e:
                        print("An sqlite3 error occurred:", e.args[0])
                    except Exception as e:
                        print("Error while adding author:", e.args[0])

            elif choice == "d":
                author_id = self.getInput("\nID to delete (empty to abort): ", allowInt=True)
                if type(author_id) is int:
                    row = self.db.getOne("SELECT id FROM authors WHERE id=?", (author_id,))
                    if row is None:
                        print("Author with given ID does not exist.")
                        continue
                    try:
                        self.db.execute('DELETE FROM authors WHERE id=?', (author_id,), True)
                        print("Author deleted.")
                        if author_id == self.currentAuthor:
                            self.currentAuthor = None
                            print("Current author reset.")
                    except ValueError:
                        print("Error: no integer ID.")
                    except Exception as e:
                        print("Error while deleting author: {}.".format(e.args[0],))

            elif choice == "c":
                if author_id is None:
                    author_id = self.getInput("\nID of new current author (empty to abort, 'u' to unset): ", allowInt=True)
                    if author_id == "":
                        continue
                    elif author_id == "u":
                        self.currentAuthor = None
                        print("Current author reset.")
                        continue
                    elif type(author_id) is not int:
                        print("Error: not a valid integer ID.")
                        continue
                c = self.db.execute("SELECT id, name FROM authors WHERE id=?", (author_id,))
                row = c.fetchone()
                if row is None:
                    print("Author with ID {} does not exist.".format(author_id))
                else:
                    self.currentAuthor = author_id
                    print("New current author:", row[1])

    def tagMenu(self, breadcrumbs):  # {{{1
        """The menu with which to alter tag information."""

        breadcrumbs = breadcrumbs[:]+["Tag"]
        choice = "h"
        while True:
            choice = self.menu(
                breadcrumbs,
                ["a - add tag          ", "l - list all tags\n",
                 "d - delete tag       ", "t - toggle tag (or simply enter the ID)\n",
                 "r - reset all tags\n"],
                silent=choice != "h", allowInt=True)

            # instead of entering "t" and then the ID, simply enter the ID
            if type(choice) is int:
                tag = choice
                choice = "t"
            else:
                tag = None

            if choice == "q":
                return
            elif choice == "l":
                print("\nALL TAGS (sorted by text):")
                c = self.db.execute("SELECT id, text FROM tags ORDER BY text")
                for row in c:
                    out = "{:>4}{}: {}".format(row[0], self.colorstring("Yellow")+"*\033[0;0m" if row[0] in self.currentTags else ' ', row[1])
                    print(out)
            elif choice == "a":
                text = self.getInput("\nTag text (empty to abort): ")
                # TODO: validate input
                if text:
                    try:
                        c = self.db.execute("INSERT INTO tags (text) VALUES (?)", (text,), True)
                        print("Tag added, new ID is", c.lastrowid)
                    except sqlite3.Error as e:
                        print("An sqlite3 error occurred:", e.args[0])
                    except Exception as e:
                        print("Error while adding tag: {}.".format(e.args[0]))
            elif choice == "d":
                tag = self.getInput("\nID to delete (empty to abort): ", allowInt=True)
                if type(tag) is not int:
                    print("Error: no integer ID.")
                else:
                    try:
                        output = ""

                        c = self.db.getOne("SELECT COUNT(*) FROM tag WHERE tag=?", (tag,))
                        if c[0] > 0:
                            dellines = self.askYesNo(
                                "Also delete the {} taglines associated with that tag?".format(c[0],),
                                allowCancel=True)
                            if dellines is False:
                                print("Deletion aborted.")
                                continue
                            if dellines == "y":
                                # delete lines of associated taglines
                                self.db.execute("""DELETE FROM lines WHERE id IN (SELECT
                                    l.id FROM lines l JOIN tag t ON t.tagline=l.tagline WHERE t.tag=?)""", (tag,))
                                # delete associated taglines
                                c = self.db.execute("""DELETE FROM taglines WHERE id IN (SELECT
                                    tl.id FROM taglines tl JOIN tag t ON t.tagline=tl.id WHERE t.tag=?)""", (tag,))
                                deleted = c.rowcount
                                output = (" and one tagline" if deleted == 1
                                          else " and {} taglines".format(deleted))
                        self.db.execute("DELETE FROM tag WHERE tag=?", (tag,))
                        self.db.execute("DELETE FROM tags WHERE id=?", (tag,), True)
                        print("Tag{} deleted.".format(output))
                    except sqlite3.Error as e:
                        print("An sqlite3 error occurred:", e.args[0])
                    except Exception as e:
                        print("Error while deleting tag: {}.".format(e.args[0]))
            elif choice == "r":
                self.currentTags = []
                print("All tags deselected.")
            elif choice == "t":
                if type(tag) is not int:
                    tag = self.getInput("\nID to toggle (empty to abort): ", allowInt=True)
                if type(tag) is int:
                    c = self.db.execute("SELECT id, text FROM tags WHERE id=?", (tag,))
                    row = c.fetchone()
                    if not row:
                        print("Error: no valid ID.")
                    else:
                        if tag in self.currentTags:
                            i = self.currentTags.index(tag)
                            self.currentTags = self.currentTags[0:i]+self.currentTags[i+1:]
                            print("Tag '{}' disabled.".format(row[1]))
                        else:
                            self.currentTags.append(tag)
                            print("Tag '{}' enabled.".format(row[1]))
                else:
                    print("Error: no integer ID.")

    def taglinesMenu(self, breadcrumbs):  # {{{1
        """The menu with which to alter the actual taglines."""

        breadcrumbs = breadcrumbs[:]+["Tagline"]
        choice ="h"
        while True:
            choice = self.menu(breadcrumbs,
                   ["l - list last taglines     ", "L - list all taglines\n",
                    "a - add new tagline        ", "any number - show tagline of that ID\n",
                    "e - edit tagline           ", "A - go to author menu\n",
                    "d - delete tagline         ", "T - go to tag menu\n"],
                    silent=choice != "h", allowInt=True)

            if choice == "q": return

            elif choice in ("l", "L") or type(choice) is int:
                print()
                q = "SELECT t.id, a.name, source, remark, date FROM taglines AS t LEFT JOIN authors AS a ON t.author=a.id"
                if choice == "l":
                    limit = self.getInput("  Number of taglines to list (default: 5): ", allowInt=True)
                    if limit is False:
                        continue
                    if type(limit) is int:
                        if limit < 0:
                            limit = 5
                    else:
                        limit = 5
                    c = self.db.execute("SELECT COUNT(id) FROM taglines")
                    r = c.fetchone()
                    q += " ORDER BY t.id LIMIT {},{}".format(max(0,r[0]-limit), limit)
                    print("LAST {} TAGLINES".format(limit))
                elif choice == "L":
                    q += " ORDER BY t.id"
                    print("ALL TAGLINES")
                else:
                    tagline = choice
                    q += " WHERE t.id='{}'".format(tagline)

                c = self.db.execute(q)
                anzahl = -1
                for index, r in enumerate(c):
                    anzahl = index
                    output = []
                    if r[1] is not None: output.append("by "+r[1])
                    if r[4] is not None: output.append("from "+r[4].isoformat())
                    if r[2] is not None: output.append("source: "+r[2])
                    if r[3] is not None: output.append("remark: "+r[3])
                    sub = self.db.execute("SELECT text FROM tags JOIN tag t ON t.tagline=? AND t.tag=tags.id ORDER BY text", (r[0],))
                    tags = sub.fetchall()
                    tags = [t[0] for t in tags]
                    if tags:
                        output.append(str("tags: "+",".join(tags)))
                    print("#{:>5}{}".format(
                        r[0], ": "+", ".join(output) if output else ""))
                    sub = self.db.execute("SELECT l.id, l.date, language, text FROM lines l LEFT JOIN taglines t ON l.tagline = t.id WHERE t.id=?", (r[0],))
                    for t in sub:
                        print("     Line  # {:>5}:{}{}: {}".format(
                            t[0],
                            " ("+t[1].isoformat()+")" if t[1] is not None else "",
                            " lang="+t[2] if t[2] is not None else "",
                            t[3] if t[3] else ""))
                if (anzahl == -1):
                    print("No match found.")

            elif choice == "a":
                self.taglineEditMenu(breadcrumbs)

            elif choice == "e":
                print("TODO :)")

            elif choice == "d":
                tagline = self.getInput("\nID to delete (d=last tagline in list, empty to abort): ", allowInt=True)
                if tagline == "":
                    continue
                if tagline == "d":
                    tagline = self.db.getOne("SELECT MAX(id) FROM taglines")[0]
                    if tagline is None:
                        print("Nothing to delete.")
                if type(tagline) is int:
                    try:
                        c = self.db.execute("SELECT id FROM taglines WHERE id=?", (tagline,))
                        if c.fetchone():
                            self.db.execute("DELETE FROM tag WHERE tagline=?", (tagline,))
                            self.db.execute("DELETE FROM lines WHERE tagline=?", (tagline,), commit=True)
                            self.db.execute('DELETE FROM taglines WHERE id=?', (tagline,))
                        print("Tagline {} and all its tag assignments deleted.".format(tagline))
                    except sqlite3.Error as e:
                        print("Error while deleting tagline: {}.".format(e.args[0]))
                else:
                    self.printWarning("Invalid choice.")

            elif choice == "A":
                self.authorMenu(breadcrumbs)

            elif choice == "T":
                self.tagMenu(breadcrumbs)

    def taglineEditMenu(self, breadcrumbs, tagline_id=None):  # {{{1
        """ Edit the content of a tagline or add a new one. """

        def ask_optional_info(source, remark, when):
            """ Ask user for content of those three field. """

            result = self.getInput("  Tagline source{}: ".format(
                "" if source is None else " [" + source + "]"))
            if result is False: return None
            source = result

            result = self.getInput("  Tagline remark{}: ".format(
                "" if remark is None else " [" + remark + "]"))
            if result is False: return None
            remark = result

            result = self.getInput("  Tagline date (yyyy-mm-dd){}: ".format(
                "" if when is None else " [" + when + "]"))
            if result is False: return None
            when = result

            return source, remark, when

        breadcrumbs = breadcrumbs[:] + ["New tagline" if tagline_id is None else "Edit tagline"]
        self.menu(breadcrumbs)

        author_name = None
        texts = {}

        if tagline_id is None:
            author_id = self.currentAuthor
            tags = self.currentTags[:]
            source = remark = when = None
        else:
            # TODO: get source, remark, when from database for given id
            pass

        if author_id is not None:
            c = self.db.execute("SELECT name FROM authors WHERE id=?", (author_id,))
            row = c.fetchone()
            if row:
                author_name = row[0]

        if len(tags) == 0:
            tag_texts = "None"
        else:
            tag_texts = ",".join([str(t) for t in tags])
            c = self.db.execute("SELECT text FROM tags WHERE id IN ("+tag_texts+") ORDER BY text")
            tag_texts = c.fetchall()
            tag_texts = ", ".join([t[0] for t in tag_texts])

        prefix = "Current" if tagline_id is None else "Tagline"
        print("{} author: {}".format(prefix, "None" if author_name is None else author_name))
        print("{} tags: {}".format(prefix, tag_texts))

        self.print(("White", "\nOptional information:"))
        if tagline_id is None:
            result = ask_optional_info(source, remark, when)
            if result is None:
                return
            source, remark, when = result
        else:
            # TODO
            pass
        print()

        noHeader = True
        # TODO: validate date

        choice = "h"
        while choice != "q":

            def enter_text(heading):
                print("    " + heading)
                language = self.getInput("    Language (ISO code): ", allowEmpty=False)
                if not language: return
                if texts.get(language):
                    if self.askYesNo("    There is already an item with this language. Overwrite it?") == "n":
                        return
                print("    Text ('r'=restart, 'c'=correct last line, 'a'=abort, 'f' or two empty lines=finish:")
                print("".join(["         {}".format(x) for x in range(1,9)]))
                print("1234567890"*8)
                lines = []
                while True:
                    line = self.getInput()
                    if line == "r":
                        lines = []
                        print("--> Input restarted.")
                    elif line == "c":
                        if lines:
                            lines.pop()
                        print("--> Last line deleted.")
                    elif line == "f" or line == "" and len(lines)>0 and lines[-1] == "":
                        texts[language] = "\n".join(lines).strip()
                        break
                    # special case for importing from a text file via copy+paste more easily
                    elif line == "---":
                        texts["de"] = "\n".join(lines).strip()
                        language = "en"
                        lines = []
                    elif line == "a": break
                    else: lines.append(line)

            choice = self.menu(breadcrumbs,
                   ["a - add an item            ", "w - save lines to database and quit menu\n",
                    "m - manage entered items   ", "q - quit to previous menu, discarding changes\n"],
                    silent=choice != "h", noHeader=noHeader)
            noHeader = False

            if choice == "a":
                enter_text("ENTER A NEW ITEM")

            elif choice == "m":
                if len(texts) == 0:
                    print("No taglines available.")
                for lang, text in texts.items():
                    print("\nLanguage: {}\n{}".format(lang, text))
                lang = self.getInput("\n   Language to delete (empty to do nothing): ")
                if texts.pop(lang, None):
                    print("Item with language '{}' deleted.".format(lang))
            elif choice == "w":
                if not texts:
                    self.printWarning("No lines to save.")
                    continue
                if tagline_id is None:
                    c = self.db.execute("INSERT INTO taglines (author,source,remark,date) values (?,?,?,?)", (
                        self.currentAuthor if self.currentAuthor else None,
                        source if source != "" else None,
                        remark if remark != "" else None,
                        when if when != "" else None), commit=True)
                    tagline_id = c.lastrowid
                    for lang, text in texts.items():
                        self.db.execute("INSERT INTO lines (tagline, date, language, text) values (?,?,?,?)",
                            (tagline_id, date.today().isoformat(), lang, text))
                    for t in tags:
                        self.db.execute("INSERT INTO tag (tag, tagline) values (?,?)", (t, tagline_id))
                    self.db.commit()
                break
            elif choice == "q":
                if texts:
                    if self.askYesNo("    This will discard your changes. Continue?", "n") != "y":
                        choice = ""

    def mainMenu(self):  # {{{1
        try:
            while True:
                bc = ["Main"]
                choice = self.menu(bc,
                        ["   a - Author menu    ", "t - Tag menu    ", "l - taglines menu"],
                        "By your command: ")
                if choice == "q":
                    self.exitTaglines()
                if choice == "a":
                    self.authorMenu(bc)
                elif choice == "t":
                    self.tagMenu(bc)
                elif choice == "l":
                    self.taglinesMenu(bc)
        except self.ExitShellUI:
            return True
        # }}}2
    # }}}1
