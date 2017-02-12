# -*- coding: utf-8 -*-

""" The terminal-based menu interface. """

from __future__ import print_function, unicode_literals
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime

from taglines.Database import DatabaseTagline

class ShellUI:  # {{{1 interactive mode
    """ Shellmode class

    It provides a hierarchy of menus which are used to inspect
    and modify the content of the database."""


    class ExitShellUI(Exception):  # {{{1
        """ Exception that is raised to leave the menu hierarchy. """

        def __init__(self):
            super(ShellUI.ExitShellUI, self).__init__()


    def __init__(self, db, editor):  # {{{1
        self.current_author = None
        self.current_keywords = []
        self.db = db
        self.db.open()
        self.editor = editor

    @staticmethod
    def colorstring(color):  # {{{1
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

    @staticmethod
    def print(what, newline=True):  # {{{1
        """ Print a string or a list of coloured strings. """

        ending = "\n" if newline else ""
        if isinstance(what, str):
            print(what, end=ending)
        else:
            if isinstance(what, tuple):
                what = [what]
            output = ""
            for part in what:
                output += "".join([
                    ShellUI.colorstring(part[0]) + part[1] + "\033[0;0m"
                    if isinstance(part, tuple) else part
                    ]) + "\033[0;0m"
            print(output, end=ending)

    @staticmethod
    def print_warning(what):  # {{{1
        """ Convenience function to print a red warning message. """

        ShellUI.print(("Red", what))

    def menu(self, breadcrumbs, choices=None, prompt="", silent=False,  # {{{1
             no_header=False, allow_int=False, allow_anything=False):
        """ Display a list of possible choices and ask user for a selection. """

        if not (silent or no_header):
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
                self.print([("Yellow", key), " - " + text if key else text], False)

        if len(breadcrumbs) == 1:  # only show in main menu
            print("\nAlso available in all menus:")
            for choice in [
                    "   q/^d - quit to parent menu   ", "Q/^c - quit program   ",
                    "h/? - show menu help"
                ]:
                key, text = choice.split(" - ")
                self.print([("Yellow", key), " - "+text], False)
            print("")

        keys.extend(["h", "?", "q"])
        while True:
            if not prompt:
                prompt = breadcrumbs[-1] + " menu choice: "
            try:
                choice = self.get_input("\n"+prompt, allow_int)
            except KeyboardInterrupt:
                choice = "Q"

            if choice is False:
                return "q"
            elif choice == "?":
                return "h"
            elif choice == "Q":
                self.exit_taglines()
                continue
            elif choice == "":
                continue
            elif choice in keys:
                return choice
            elif allow_int:
                try:
                    return int(choice)
                except ValueError:
                    if allow_anything:
                        return choice
                    pass
            elif allow_anything:
                return choice
            else:
                self.print_warning("Invalid choice.")

    @staticmethod
    def get_input(text="", allow_empty=True, allow_int=False):  # {{{1
        """ This is a shared function to get user input and catch Ctrl+C/D.

        @param allow_empty: whether the input may be the empty string
        @param allow_int: whether to accept numeric input and convert it to
                          int automatically
        """

        while True:
            try:
                ShellUI.print(("green", text), False)
                if sys.version_info.major == 2:
                    choice = raw_input()
                else:
                    choice = input()

                if not allow_empty and not choice:
                    print("Empty string not allowed here.")
                else:
                    if sys.version_info.major == 2:
                        choice = choice.decode("utf-8")
                    if allow_int:
                        try:
                            choice = int(choice)
                            return choice
                        except ValueError:
                            pass
                    return choice
            # Ctrl+C
            except KeyboardInterrupt:
                print()
                ShellUI.exit_taglines()
            # Ctrl+D
            except EOFError:
                print()
                return False

    def ask_yesno(self, text, default="n", allow_cancel=False):  # {{{1
        """ Ask a yes/no question, digest the answer and return the answer.

        default should be either "y" or "n" to set the relevant answer. """

        suffix = ["Y" if default == "y" else "y",
                  "N" if default == "n" else "n"]
        if allow_cancel:
            suffix.append("^d")
        text += "  [" + "/".join(suffix) + "] "

        while True:
            choice = self.get_input(text)
            if not choice:
                if choice is False and allow_cancel:
                    return False
                choice = default
            if choice:
                if "yes".startswith(choice.lower()):
                    choice = "y"
                elif "no".startswith(choice.lower()):
                    choice = "n"
                else:
                    choice = ""
            if choice == "":
                print("Please answer yes or no.")
            else:
                return choice

    @ staticmethod
    def exit_taglines():  # {{{1
        """ Ask for exit confirmation and exit on positive answer. """

        try:
            # not using ask_yesno b/c of own handling of Ctrl+C/D
            ShellUI.print(("green", "\nReally quit Taglines?  [y/N] "), False)
            if sys.version_info.major == 2:
                # pylint: disable=undefined-variable
                i = raw_input()
            else:
                i = input()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if i and "yes".startswith(i.lower()):
            raise ShellUI.ExitShellUI()

    def author_menu(self, breadcrumbs):  # {{{1
        """ The menu with which to alter author information. """

        breadcrumbs = breadcrumbs[:]+["Author"]
        choice = "h"
        while True:
            choice = self.menu(
                breadcrumbs,
                ["a - add author      ", "l - list all authors\n",
                 "d - delete author   ", "c - set current author for new taglines\n"],
                silent=choice != "h", allow_int=True)

            if isinstance(choice, int):
                author_id = choice
                choice = "c"
            else:
                author_id = None

            if choice == "a":
                name = self.get_input("\nName (empty to abort): ")
                if name != False and name != "":
                    try:
                        born = self.get_input("Year of birth: ")
                        if born == False:
                            continue
                        else:
                            born = int(born)
                    except ValueError:
                        born = None
                    try:
                        died = self.get_input("Year of death: ")
                        if died == False:
                            continue
                        else:
                            died = int(died)
                    except ValueError:
                        died = None
                    try:
                        cursor = self.db.execute(
                            "INSERT INTO authors (name, born, died) VALUES (?,?,?)", (
                                name, born, died), True)
                        print("Author added, new ID is {}".format(cursor.lastrowid))
                    except sqlite3.Error as error:
                        print("An sqlite3 error occurred:", error.args[0])

            elif choice == "c":
                if author_id is None:
                    author_id = self.get_input(
                        "\nID of new current author (empty to abort, 'u' to unset): ",
                        allow_int=True)
                    if author_id == "":
                        continue
                    elif author_id == "u":
                        self.current_author = None
                        print("Current author reset.")
                        continue
                    elif not isinstance(author_id, int):
                        print("Error: not a valid integer ID.")
                        continue
                row = self.db.get_one("SELECT id, name FROM authors WHERE id=?", (author_id,))
                if row is None:
                    print("Author with ID {} does not exist.".format(author_id))
                else:
                    self.current_author = author_id
                    print("New current author:", row[1])

            elif choice == "d":
                author_id = self.get_input("\nID to delete (empty to abort): ", allow_int=True)
                if author_id == "":
                    continue
                if isinstance(author_id, int):
                    row = self.db.get_one("SELECT id FROM authors WHERE id=?", (author_id,))
                    if row is None:
                        print("Author with given ID does not exist.")
                        continue
                    try:
                        self.db.execute('DELETE FROM authors WHERE id=?', (author_id,), True)
                        print("Author deleted.")
                        if author_id == self.current_author:
                            self.current_author = None
                            print("Current author reset.")
                    except ValueError:
                        print("Error: no integer ID.")

            elif choice == "l":
                print("\nALL AUTHORS (sorted by name):")
                cursor = self.db.execute("SELECT id, name, born, died FROM authors ORDER BY name")
                for row in cursor:
                    out = "{:>4}{}: {}".format(
                        row[0],
                        self.colorstring("Yellow")+"*\033[0;0m"
                        if self.current_author == row[0] else ' ',
                        row[1])
                    if row[2] is not None or row[3] is not None:
                        out += " (" + str(row[2]) + "-" + str(row[3]) + ")"
                    print(out)

            elif choice == "q":
                return

    def keyword_menu(self, breadcrumbs):  # {{{1
        """ The menu with which to alter keyword information. """

        breadcrumbs = breadcrumbs[:]+["Keyword"]
        choice = "h"
        while True:
            choice = self.menu(
                breadcrumbs,
                ["a - add keyword      ", "l - list all keywords\n",
                 "d - delete keyword   ", "t - toggle keyword (or simply enter the ID or name)\n",
                 "r - reset all keywords\n"],
                silent=choice != "h", allow_anything=True, allow_int=True)

            # instead of entering "t" and then the ID, simply enter the ID
            if isinstance(choice, int):
                keyword = choice
                choice = "t"
            else:
                keyword = None

            if choice == "a":
                text = self.get_input("\nKeyword text (empty to abort): ")
                if text:
                    try:
                        cursor = self.db.execute(
                            "INSERT INTO keywords (text) VALUES (?)", (text,), True)
                        print("Keyword added, new ID is", cursor.lastrowid)
                    except sqlite3.Error as error:
                        print("An sqlite3 error occurred:", error.args[0])

            elif choice == "d":
                keyword = self.get_input("\nID to delete (empty to abort): ", allow_empty=True, allow_int=True)
                if keyword == "":
                    continue
                if not isinstance(keyword, int):
                    print("Error: no integer ID.")
                else:
                    try:
                        output = ""

                        cursor = self.db.get_one("SELECT COUNT(*) FROM kw_tl WHERE keyword=?", (keyword,))
                        if cursor[0] > 0:
                            dellines = self.ask_yesno(
                                "Also delete the {} taglines associated with that keyword?".format(
                                    cursor[0],),
                                allow_cancel=True)
                            if dellines is False:
                                print("Deletion aborted.")
                                continue
                            if dellines == "y":
                                # delete lines of associated taglines
                                self.db.execute("""DELETE FROM lines WHERE id IN (SELECT
                                    l.id FROM lines l JOIN kw_tl k ON k.tagline=l.tagline
                                    WHERE k.keyword=?)""", (keyword,))
                                # delete associated taglines
                                cursor = self.db.execute("""DELETE FROM taglines WHERE id IN (SELECT
                                    tl.id FROM taglines tl JOIN kw_tl k ON k.tagline=tl.id
                                    WHERE k.keyword=?)""", (keyword,))
                                deleted = cursor.rowcount
                                output = (" and one tagline" if deleted == 1
                                          else " and {} taglines".format(deleted))
                        self.db.execute("DELETE FROM kw_tl WHERE keyword=?", (keyword,))
                        self.db.execute("DELETE FROM keywords WHERE id=?", (keyword,), True)
                        print("Keyword{} deleted.".format(output))
                    except sqlite3.Error as error:
                        print("An sqlite3 error occurred:", error.args[0])

            elif choice == "l":
                print("\nALL KEYWORDS (sorted by text):")
                cursor = self.db.execute("SELECT id, text FROM keywords ORDER BY text")
                for row in cursor:
                    out = "{:>4}{}: {}".format(
                        row[0],
                        self.colorstring("Yellow")+"*\033[0;0m"
                        if row[0] in self.current_keywords else ' ', row[1])
                    print(out)

            elif choice == "r":
                self.current_keywords = []
                print("All keywords deselected.")

            elif choice == "q":
                return

            else:
                if not choice == "t":
                    # a keyword name was given
                    row = self.db.get_one("SELECT id FROM keywords WHERE text=?", (choice,))
                    if not row:
                        print("Error: no valid keyword name.")
                        continue
                    keyword = row[0]

                if not isinstance(keyword, int):
                    keyword = self.get_input("\nID to toggle (empty to abort): ", allow_int=True)
                if isinstance(keyword, int):
                    row = self.db.get_one("SELECT id, text FROM keywords WHERE id=?", (keyword,))
                    if not row:
                        print("Error: no valid ID.")
                    else:
                        if keyword in self.current_keywords:
                            i = self.current_keywords.index(keyword)
                            self.current_keywords = self.current_keywords[0:i] + self.current_keywords[i+1:]
                            print("Keyword '{}' disabled.".format(row[1]))
                        else:
                            self.current_keywords.append(keyword)
                            print("Keyword '{}' enabled.".format(row[1]))
                else:
                    print("Error: no integer ID.")

    def taglines_menu(self, breadcrumbs):  # {{{1
        """ The menu with which to alter the actual taglines. """

        breadcrumbs = breadcrumbs[:]+["Tagline"]
        choice = "h"
        while True:
            choice = self.menu(breadcrumbs, [
                "l - list last taglines     ", "L - list all taglines\n",
                "a - add new tagline        ", "any number - show tagline of that ID\n",
                "e - edit tagline           ", "A - go to author menu\n",
                "d - delete tagline         ", "K - go to keyword menu\n"
                ], silent=choice != "h", allow_int=True)

            if choice == "A":
                self.author_menu(breadcrumbs)

            elif choice == "K":
                self.keyword_menu(breadcrumbs)

            elif choice == "a":
                self.tagline_edit_menu(breadcrumbs)

            elif choice == "d":
                tagline = self.get_input(
                    "\nID to delete (d=last tagline in list, empty to abort): ", allow_int=True)
                if tagline == "":
                    continue
                if tagline == "d":
                    tagline = self.db.get_one("SELECT MAX(id) FROM taglines")[0]
                    if tagline is None:
                        print("Nothing to delete.")
                if isinstance(tagline, int):
                    try:
                        if self.db.get_one("SELECT id FROM taglines WHERE id=?", (tagline,)):
                            self.db.execute("DELETE FROM kw_tl WHERE tagline=?", (tagline,))
                            self.db.execute("DELETE FROM lines WHERE tagline=?", (tagline,), commit=True)
                            self.db.execute('DELETE FROM taglines WHERE id=?', (tagline,))
                        print("Tagline {} and all its keyword assignments deleted.".format(tagline))
                    except sqlite3.Error as error:
                        print("Error while deleting tagline: {}.".format(error.args[0]))
                else:
                    self.print_warning("Invalid choice.")

            elif choice == "e":
                tagline = self.get_input(
                    "  ID of tagline to edit (empty to abort, "
                    "-1 for the most recent tagline change): ", allow_int=True)
                if not tagline:
                    continue
                if isinstance(tagline, int):
                    if tagline == -1:
                        row = self.db.get_one(
                            "SELECT tagline FROM lines ORDER BY date DESC LIMIT 1")
                    else:
                        row = self.db.get_one("SELECT id FROM taglines WHERE id=?", (tagline,))
                    if row:
                        tagline = row[0]
                        self.tagline_edit_menu(breadcrumbs, tagline)
                    else:
                        print("Invalid ID.")
                else:
                    print("Invalid ID.")

            elif choice in ("l", "L") or isinstance(choice, int):
                print()
                query = """SELECT t.id, a.name, source, remark, date FROM taglines AS t
                LEFT JOIN authors AS a ON t.author=a.id"""
                if choice == "l":
                    limit = self.get_input(
                        "  Number of taglines to list (default: 5): ", allow_int=True)
                    if limit is False:
                        continue
                    if isinstance(limit, int):
                        if limit < 0:
                            limit = 5
                    else:
                        limit = 5
                    row = self.db.get_one("SELECT COUNT(id) FROM taglines")
                    query += " ORDER BY t.id LIMIT {},{}".format(max(0, row[0] - limit), limit)
                    print("LAST {} TAGLINES".format(limit))
                elif choice == "L":
                    query += " ORDER BY t.id"
                    print("ALL TAGLINES")
                else:
                    tagline = choice
                    query += " WHERE t.id='{}'".format(tagline)

                cursor = self.db.execute(query)
                anzahl = -1
                for index, row in enumerate(cursor):
                    anzahl = index
                    output = []
                    if row[1] is not None: output.append("by "+row[1])
                    if row[4] is not None: output.append("from "+row[4].isoformat())
                    if row[2] is not None: output.append("source: "+row[2])
                    if row[3] is not None: output.append("remark: "+row[3])
                    sub = self.db.execute(
                        "SELECT text FROM keywords JOIN kw_tl k ON k.tagline=? AND k.keyword=keywords.id "
                        "ORDER BY text", (row[0],))
                    keywords = sub.fetchall()
                    keywords = [keyword[0] for keyword in keywords]
                    if keywords:
                        output.append(str("keywords: " + ", ".join(keywords)))
                    print("#{:>5}{}".format(
                        row[0], ": "+", ".join(output) if output else ""))
                    sub = self.db.execute(
                        "SELECT l.id, l.date, language, text FROM lines l "
                        "LEFT JOIN taglines t ON l.tagline = t.id WHERE t.id=?", (row[0],))
                    for keyword in sub:
                        print("     Line  # {:>5}:{}{}: {}".format(
                            keyword[0],
                            " ("+keyword[1].isoformat()+")" if keyword[1] is not None else "",
                            " lang="+keyword[2] if keyword[2] is not None else "",
                            keyword[3] if keyword[3] else ""))
                if anzahl == -1:
                    print("No match found.")

            elif choice == "q":
                return

    def tagline_edit_menu(self, breadcrumbs, tagline_id=None):  # {{{1
        """ Edit the content of a tagline or add a new one. """

        def ask_optional_info(source, remark, when):
            """ Ask user for content of those three field. """

            result = self.get_input("  Tagline source{}: ".format(
                "" if source is None else " [" + source + "]"))
            if result is False: return None
            source = result

            result = self.get_input("  Tagline remark{}: ".format(
                "" if remark is None else " [" + remark + "]"))
            if result is False: return None
            remark = result

            while True:
                result = self.get_input("  Tagline date (yyyy-mm-dd){}: ".format(
                    "" if when is None else " [" + when.strftime('%F') + "]"))
                if result is False: return None
                if result:
                    try:
                        when = datetime.strptime(result, '%Y-%m-%d').date()
                        break
                    except ValueError:
                        self.print_warning('Not a valid date.')
                else:
                    when = None
                    break

            return source, remark, when

        breadcrumbs = breadcrumbs[:] + ["New tagline" if tagline_id is None else "Edit tagline"]
        self.menu(breadcrumbs)

        tagline = DatabaseTagline(
            self.db, tagline_id, self.current_author, self.current_keywords[:])

        if len(tagline.keywords) == 0:
            keyword_texts = "None"
        else:
            keyword_texts = ",".join([str(keyword) for keyword in tagline.keywords])
            cursor = self.db.execute(
                "SELECT text FROM keywords WHERE id IN (" + keyword_texts + ") ORDER BY text")
            keyword_texts = ", ".join([text[0] for text in cursor.fetchall()])

        prefix = "Current" if tagline_id is None else "Tagline"
        print("{} author: {}".format(
            prefix, "None" if tagline.author_name is None else tagline.author_name))
        print("{} keywords: {}".format(prefix, keyword_texts))

        self.print(("White", "\nOptional information:"))
        if tagline_id is None:
            result = ask_optional_info(tagline.source, tagline.remark, tagline.when)
            if result is None:
                return
            tagline.set_information(*result)
        else:
            self.print("  Tagline source:", tagline.source)
            self.print("  Tagline remark:", tagline.remark)
            self.print("  Tagline date:", tagline.when)
        print()

        no_header = True
        choice = "h"
        while choice != "q":

            def enter_text(heading, language="", existing_langs=None):
                """ Tagline entry mask to enter several lines of text. """

                print("    " + heading)
                new_language = self.get_input("    Language (ISO code){}: ".format(
                    " [" + language + "]" if language else ""), allow_empty=False)
                if new_language == "":
                    new_language = language
                if not new_language:
                    return
                if existing_langs and new_language in existing_langs and new_language != language:
                    if self.ask_yesno(
                            "    There is already an item with this language. "
                            "Overwrite it?") == "n":
                        return

                lines = []
                if self.editor == '-':
                    pass
                elif self.editor:
                    with tempfile.NamedTemporaryFile(mode='w+t', prefix='taglines.') as handle:
                        try:
                            # allow for arguments to editor itself
                            subprocess.check_call(
                                self.editor.split() + [handle.name])
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            self.print_warning(
                                "Could not open editor. Continuing with internal menu."
                                )
                        else:
                            handle.file.seek(0)
                            lines = handle.file.read().strip()
                            if lines:
                                return (new_language, lines)
                            else:
                                self.print_warning(
                                    'Did no receive anything from editor, '
                                    'using internal menu.')
                                # nothing was entered
                                lines = []
                else:
                    print("EDITOR is not set, using internal menu.")
                    print()

                print("    Text ('r'=restart, 'c'=correct last line, "
                      "'a'=abort, 'f' or two empty lines=finish:")
                print("".join(["         {}".format(x) for x in range(1, 9)]))
                print("1234567890"*8)
                while True:
                    line = self.get_input()
                    if line == "a":
                        break

                    elif line == "c":
                        if lines:
                            lines.pop()
                        print("--> Last line deleted.")

                    elif line == "f" or line == "" and len(lines) > 0 and lines[-1] == "":
                        return (new_language, "\n".join(lines).strip())

                    elif line == "r":
                        lines = []
                        print("--> Input restarted.")

                    else:
                        lines.append(line)

            choice = self.menu(breadcrumbs, [
                "a - add a tagline text      ", "k - edit keywords\n",
                "m - manage tagline texts    ", "w - save changes to database and quit menu\n",
                "o - edit optional inform.   ", "q - quit to previous menu, discarding changes\n"
                ], silent=choice != "h", no_header=no_header)
            no_header = False

            if choice == "a":
                result = enter_text("ENTER A NEW ITEM", existing_langs=tagline.texts)
                if result is not None:
                    tagline.set_text(*result)

            elif choice == "m":
                if len(tagline.texts) == 0:
                    print("No taglines available.")
                for lang in tagline.texts:
                    text = tagline.texts.get(lang)
                    print("\nLanguage: {}{}\n{}".format(
                        lang, " (unsaved)" if text[1] else "", text[0]))

                choice = "h"
                while True:
                    choice = self.menu(breadcrumbs + ["Modify tagline texts"], [
                        "d - delete a text   ", "l - list texts\n",
                        "m - modify a text   ", "q - quit menu\n",
                        ], silent=choice != "h", no_header=no_header)

                    if choice == "":
                        continue

                    elif choice == "d":
                        lang = self.get_input("   Language to delete ({}): ".format(
                            ", ".join(tagline.texts.keys())))
                        if tagline.pop_text(lang) is None:
                            print("Invalid language.")
                        else:
                            print("Item with language '{}' deleted.".format(lang))

                    elif choice == "l":
                        if len(tagline.texts) == 0:
                            print("No taglines available.")
                            continue
                        for lang in tagline.texts:
                            text = tagline.texts[lang]
                            print("\nLanguage: {}{}\n{}".format(
                                lang, " (unsaved)" if text[1] else "", text[0]))

                    elif choice == "m":
                        lang = self.get_input("   Language to modify ({}): ".format(
                            ", ".join(tagline.texts)))
                        if lang in tagline.texts:
                            result = enter_text("EDIT TEXT", lang, tagline.texts)
                            if result is not None:
                                tagline.set_text(*result, old_language=lang)
                        else:
                            print("Invalid language.")

                    elif choice == "q":
                        break

                choice = "h"

            elif choice == "k":
                print("Sorry, not implemented yet.")

            elif choice == "o":
                result = ask_optional_info(
                    tagline.source, tagline.remark, tagline.when)
                if result is not None:
                    tagline.set_information(*result)

            elif choice == "q":
                if tagline.is_changed:
                    if self.ask_yesno("    Tagline has unsaved changes. Continue?", "n") != "y":
                        choice = ""

            elif choice == "w":
                if not tagline.is_changed:
                    print("No changes to save.")
                else:
                    tagline.commit()
                    print("Changes saved.")
                break

    def main_menu(self):  # {{{1
        """ The main menu loop for the terminal interface. """

        try:
            while True:
                breadcrumbs = ["Main"]
                choice = self.menu(breadcrumbs, [
                    "   a - Author menu    ", "k - Keyword menu    ", "l - taglines menu",
                    ], "By your command: ")
                if choice == "a":
                    self.author_menu(breadcrumbs)
                elif choice == "l":
                    self.taglines_menu(breadcrumbs)
                elif choice == "q":
                    self.exit_taglines()
                elif choice == "k":
                    self.keyword_menu(breadcrumbs)
        except self.ExitShellUI:
            return True
        # }}}2
    # }}}1
