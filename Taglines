#!/usr/bin/python3
# -*- coding: utf-8 -*-

import taglines
from taglines.ArgParser import ArgParser
from taglines.ShellUI import ShellUI

parser = ArgParser()
args = parser.args

import os
from datetime import date

#}}}1

# create a new sqlite database file {{{1
# ----------------------------------------------------------------

if args.init:
    if os.path.exists(args.file):
        ok = input("Warning: "+args.file+" already exists. Overwrite? [y/N] ")
        if ok and "yes".startswith(ok.lower()):
            try:
                os.remove( args.file )
            except OSError as e:
                exit("Error: could not delete old file: {0}. Exiting.".format(e.args[1]))
        else:
            print("good bye")
            exit(1)
    db = taglines.Database()
    db.initialiseFile(args.file)
    exit(0)


# retrieve one random tagline, then exit {{{1
if args.random:
    db = taglines.Database(args.file)
    if db:
        db.parseArguments(args)
        print(db.randomTagline())

if args.list:
    db = taglines.Database(args.file)
    if db:
        db.parseArguments(args)

        first=True
        for r in db.taglines():
            if first:
                first=False
            else:
                print("%")
            print(r[0])
        exit(0)


# stand-alone DB functions {{{1
# ----------------------------------------------------------------
if args.show_tags:
    db = taglines.Database(args.file);
    if db:
        for tag in db.tags(orderByName = True): print(tag)
    exit(0)


if args.show_authors:
    db = taglines.Database(args.file);
    if db:
        for author in db.authors(): print(author)
    exit(0)

if args.stats:
    db = taglines.Database(args.file);
    if db:
        stats = db.stats()

        print("Number of taglines:        {0:6d}".format(stats["tagline count"],))
        print("Number of texts:           {0:6d}   (ø {1:5.2f} per tagline)".format(
            stats["line count"], stats["line count"]/stats["tagline count"]))
        print("Average text length:       {0:8.1f}".format(stats["avg tagline length"],))
        print("Number of tags:            {0:6d}".format(stats["tag count"],))
        print("Number of tag assignments: {0:6d}   (ø {1:5.2f} per tagline)".format(
            stats["tag assignments"], stats["tag assignments"]/stats["tagline count"]))
        print("Number of authors:         {0:6d}".format(stats["author count"],))
        print("Used languages:            {0:6d}".format(stats["language count"],))
        exit(0)




if args.interactive:
    db = taglines.Database(args.file);
    if db:
        shell = ShellUI(db)
    shell.mainMenu()
    exit(0)
