""" This class prints and parses command line arguments. """

import argparse
from os import getenv

def parse_arguments():
    """ Parse arguments passed to Taglines. """

    parser = argparse.ArgumentParser(
        description='An sqlite3 based taglines generator and manager.',
        prog="Taglines")

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-L', '--list', action='store_true',
        help='List all found items in fortunes format')
    group.add_argument(
        '-r', '--random', action='store_true',
        help='From the found items, show one at random (default)')
    group.add_argument(
        '--show-tags', action='store_true',
        help='List all available tags in the database and exit')
    group.add_argument(
        '--show-authors', action='store_true',
        help='List all available authors in the database and exit')
    group.add_argument(
        '--stats', action='store_true',
        help='Show some statistics about the database')
    group.add_argument(
        '--init', action='store_true',
        help='Initialise a new database file')
    group.add_argument(
        '-i', '--interactive', action='store_true',
        help='Go into interactive mode (simple shell)')
    parser.add_argument(
        '-E', '--editor', default=getenv('EDITOR'),
        help='External editor to use. Default taken from environment, set to '
             '"-" to disable external editor. May contain arguments to editor, '
             'e.g. "vim -X."')
    parser.add_argument(
        '-o', '--ortag', action='store_true',
        help='Combine several tags with OR instead of AND')
    parser.add_argument(
        '-t', '--tag', action='append',
        help='Only show items with the given tag(s)')
    parser.add_argument(
        '-T', '--text', action='append',
        help='Search for given text (combined with AND. Only a word: search as '
             'substring, %% at start or end: search at end or start of text, '
             'respectively, i.e. SQL-syntax)')
    parser.add_argument(
        '-a', '--author',
        help='Only show items by the given author')
    parser.add_argument(
        '-e', '--exactauthor', action='store_true',
        help='Look for exact author match')
    parser.add_argument(
        '-l', '--lang',
        help='Only show items with the given language')
    parser.add_argument(
        '-s', '--sort', choices=['a', 'l', 't'],
        help='Sort output by author, language or text')
    parser.add_argument(
        'file',
        help='An sqlite3 database file')
    #group=parser.add_argument_group('Actions')
    #group=parser.add_mutually_exclusive_group()

    return parser.parse_args()
