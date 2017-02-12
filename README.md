taglines – fortunes with a database
===================================

https://github.com/felf/taglines
Copyright © 2011–2017 Frank Steinmetzger

Synopsis
--------
With Taglines you can manage a database of fortunes, enriched with metadata for
filtering and retrieval. It is written in Python and works with python 2 and 3.

Installation
------------
Change into the source directory and run

    $ python setup.py install

Possibly run as root or with sudo, depending on your installation prefix. For
more information please refer to the [setuptools](
https://github.com/pypa/setuptools) documentation.

How to use Taglines
-------------------
Taglines has a built-in help:

    $ Taglines -h

When running Taglines, you must give it a filename for the database and an
operation mode, which is one of:
* initialise the database file (`Taglines --init`)
* open the db interactively to edit items or enter new ones (`Taglines -i`)
* print database statistics (`Taglines --stats`)
* list all items in ye olde flat fortune format (`Taglines -L`)
* print a random item (`Taglines -r`)

For the output operations, you can narrow down the list of candidates by
passing selectors, i.e. keywords, language, author or words to match.

There are three menus in which you can enter new data.

<b>Author</b>
Use this menu to enter new authors, or to manage existing ones. Here you also
set the <i>current author</i>, which is marked with a "`*`" when you list all
authors and which will be assigned automatically when you create a new tagline.

<b>Keywords</b>
You can assign any number of keywords to a tagline which will make it easier to
find a suitable tagline in the database later on. Use this menu to create, edit
and delete tags and to set them active. Active keywords are marked with a "`*`"
when you list all keywords and they will be assigned automatically when you
create a new tagline.

<b>Tagline</b>
Use this menu to enter new taglines or edit or delete existing ones. Each
tagline carries has a number of optional information:
* source: a simple text in which you can describe where the tagline is from,
* author: who dunnit,
* date: when the tagline came into existence originally,
* the date at which you add the tagline to the database. This one is read-only.
And then of course there is the actual text. You can enter it in several
languages, identified by the langauge ISO code (en, de, fr, ja, etc).

When entering many taglines in a row, the user may often need to change the
current author and active keywords from one tagline to the next. Therefore,
those two menus are avaible as a submenu right in the Tagline menu, removing
the need to go back over the main menu.

Each and every menu accepts the following common inputs:
* `q` or `^d`: exit menu to parent (or quit if in topmost menu)
* `Q` or `^c`: quit program without saving
* `?` or `h`: print list of actions available in the current menu

How does Taglines work?
-----------------------
Taglines uses sqlite as its "file format" to store taglines and associate them
with various kinds of metadata. In essence, Taglines is a glorified interface
to a database schema. :o)

A "tagline" in the context of this program is a collection of texts whose
content is the same, but expressed in different langauges. A tagline example
could be:
    en: "Hello World"
    de: "Hallo Welt"
    fr: "Bonjour, le monde"

The user interface is rather crude, using a simple letter-based menu
navigation. Like with many tools written for personal use, it emerged out of
necessity to do a job quick and dirty. On the other hand, the UI makes it quite
efficient to enter many taglines in one session, once you know how to navigate
through the menu. To improve usability, colours and a breadcrumb line at the
top of the menu are employed.

The quickest way to enter many taglines at once would be to prepare the texts
in an editor, insert the menu commands between the texts and then paste the
whole thing into the terminal. I used this when I mass-imported my old fortune
files. This is the main reason why I kept the internal menu around after I
implemented the use of an external editor.

How came Taglines into being?
-----------------------------
In my early Linux days I found out about the [fortunes](
https://en.wikipedia.org/wiki/Fortune_(Unix)) program, which reads a
specially formatted text file, randomly picks an item from that file and prints
it to stdout. I am a fun guy, always on the lookout for a joke. And so, I
started using fortune to add a little joke or pun to every e-mail I send (such
little phrases, wisdoms or jokes in the signature are called taglines).

Over time, my tagline collection grew and grew, whilst I became active in
international communities, at first in newsgroups, later in mailing lists. And
the people there don’t necessarily understand jokes in my native language of
German. At first I used separate fortune files to keep German and English
apart, but this is a mess, as id made keeping the files in sync difficult: I
need to keep track of translations, and based on which criterion would the
items in the file be sorted?

And so, Taglines became one of the first tools I wrote using Python and sqlite.
It fills that gap by storing everything in one file, keeping the different
translations of one and the same text semantically together and keep track of
where I got a certain text from. I also allows to choose a tagline by topic, by
way of applying keywords to the taglines. So in a linux mailing list, I could
restrict tagline selection to English computer and math jokes, whereas in a
mailing list for a local choir, I would only use music jokes in German.

Hacking
-------
Feel free to add new stuff or clean up the code mess that I created. :o)

Reporting bugs
--------------
You can use github’s facilities, drop me a mail or submit a pull request with
your own fix. ;-)

TODOs
-----
Here are some notable ToDos:
* I started a qt interface to have a more convenient way of correcting existing
  taglines, which unto now is still a bit clunky. But it has never gotten fully
  off the ground and currently I use sqlitebrowser to do quick corrections.
* Make data entry more robust, particularly date input.
* Localisation
