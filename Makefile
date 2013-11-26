gettext:
	xgettext -L Python Taglines taglines/*.py -o po/template.pot
	msgmerge -U po/de.po po/template.pot

mos:
	msgfmt po/de.po -o mo/de.mo

setup:
	python3 setup.py install

install: mos setup
	install -T mo/de.mo /usr/share/locale/de/LC_MESSAGES/Taglines.mo

uninstall:
	rm /usr/bin/Taglines
	rm -rf /usr/lib64/python3.2/site-packages/taglines
	rm /usr/share/locale/de/LC_MESSAGES/Taglines.mo

dist:
	./setup.py sdist

# TODO: wildcard-target für *.mo erzeugen
