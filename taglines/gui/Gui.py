""" The graphic user interface, built with Qt. """

try:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
except ImportError:
    print("PyQt modules not found.  Cannot start graphical interface.")
    exit(1)

try:
    # if available, replace Qt file dialogues with the more sophisticated KDE version
    from PyKDE4.kio import KFileDialog
    kde = True
#       from PyKDE4.kdecore import *
except ImportError:
    kde = False

import sys, taglines

class AuthorModel(QAbstractItemModel): #{{{1
    """
    This class is the interface to the authors in the database

    It allows to select one and only one author for a tagline.
    """
    def __init__(self, parent):
        QAbstractItemModel.__init__(self, parent)
        self.parent = parent
        self.authors=[
            (-2, '(Don\'t filter)', None, None),
            (-1, '(None)', None, None)]
        self.setHeaderData(0, Qt.Horizontal, "ID",   Qt.DisplayRole)
        self.setHeaderData(1, Qt.Horizontal, "Name", Qt.DisplayRole)
        self.setHeaderData(2, Qt.Horizontal, "Born", Qt.DisplayRole)
        self.setHeaderData(3, Qt.Horizontal, "Died", Qt.DisplayRole)
    def add(self, author):
        if author[0]!=-1 or not self.db: return False
        count = self.rowCount()
        self.beginInsertRows(QModelIndex(), count, count)
        c = self.db.cursor()
        c.execute("INSERT INTO authors (name, born, died) values (?,?,?)",
            tuple(author[1:4]))
        author[0] = c.lastrowid
        self.authors.append(author)
        self.endInsertRows()
        self.emit(SIGNAL("rowsInserted()"))
        return True
    def set(self, author):
        self.db.execute(
            "UPDATE authors SET name=?, born=?, died=? WHERE id=?",
            tuple(author[1:]+author[0:1]))
        self.emit(SIGNAL("dataChanged()"))
        return True
    def delete(self, index, taglines):
        if not index.isValid(): return False
        author = self.authors[index.row()][0]
        self.beginRemoveRows(QModelIndex(), index.row(), index.row())
        if taglines:
            # delete all tags assigned to the author's taglines
            self.db.execute("""DELETE FROM tag WHERE id IN (
                SELECT t.id FROM TAG t
                    JOIN taglines tl ON t.tagline=tl.id
                    JOIN authors a ON tl.author=a.id
                    WHERE a.id=?)""", (author,))
            # delete all lines associated with the author's taglines
            self.db.execute("""DELETE FROM lines WHERE id IN (
                SELECT l.id FROM lines l
                    JOIN taglines tl ON l.tagline=tl.id
                    JOIN authors a ON tl.author=a.id
                    WHERE a.id=?)""", (author,))
            # delete author's taglines
            self.db.execute("DELETE FROM taglines WHERE author=?", (author,))
        else:
            # remove author references from taglines
            self.db.execute(
                "UPDATE taglines SET author=NULL WHERE author=?", (author,))
        self.db.execute("DELETE FROM authors WHERE id=?", (author,))
        self.authors[index.row():index.row()+1]=[]
        self.endRemoveRows()
        self.emit(SIGNAL("rowsDeleted()"))
        return True
    def get(self, index):
        if not index.isValid(): return False
        return self.authors[index.row()]
    def setDB(self, db):
        self.db = db
        authors=[
            (-2, '(Don\'t filter)', None, None),
            (-1, '(None)', None, None)]
        for r in self.db.execute("SELECT * FROM authors"):
            authors.append(list(r))
        self.beginResetModel()
        self.authors = authors
        self.endResetModel()
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        if role==Qt.TextAlignmentRole:
            return Qt.AlignLeft if index.column()==1 else Qt.AlignRight
        elif role!=Qt.DisplayRole: return None
        return self.authors[index.row()][index.column()]
    def hasChildren(self, index):
        return not index.isValid();
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role==Qt.DisplayRole and orientation==Qt.Horizontal:
            return ("ID", "Name", "Born", "Died")[section]
    def index(self, row, column, parent=QModelIndex()):
        if row>=len(self.authors) or row<0 or column<0 or column>3:
            return QModelIndex()
        return self.createIndex(row, column, self.authors[row]);
    def parent(self, index):
        return QModelIndex()
    def columnCount(self, parent=QModelIndex()):
        return 4
    def rowCount(self, parent=QModelIndex()):
        return len(self.authors)
    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid(): return False
        if role!=Qt.EditRole: return False
        if index.column()==0:
            return False
        elif index.column()==1:
            value = unicode(value.toString()).strip()
        else:
            value = value.toInt()
        author=self.authors[index.row()]
        author[index.column()] = value;
        self.db.execute("UPDATE authors SET " +
            ["name", "born", "died"][author[0]] +
            " = ? WHERE id = ?", (value, author[0]))
        self.parent.changed = True
        self.emit(SIGNAL("dataChanged(QModelIndex)"), index)
        return True

class AuthorProxyModel(QSortFilterProxyModel): #{{{1
    """
    This proxy sorts the author data and filters out the virtual entries
    which cannot be edited, depending on setting.
    """
    def __init__(self, parent, showVirtual = False):
        QSortFilterProxyModel.__init__(self, parent)
        self.setDynamicSortFilter(True)
        self.showVirtual = showVirtual
        self.sort(1, Qt.AscendingOrder)
    def filterAcceptsRow(self, row, parent):
        return self.showVirtual or int(self.sourceModel().data(
            self.sourceModel().index(row, 0, parent)))>=0

class LanguagesModel(QAbstractItemModel): #{{{1
    """
    This class is the interface to the languages in the database

    It allows to select a number of languages for a tagline.
    """
    def __init__(self, parent):
        QAbstractItemModel.__init__(self, parent)
        self.setHeaderData(0, Qt.Horizontal, "Name", Qt.DisplayRole)
    def setDB(self, db):
        self.db = db
        self.languages=[]
        for r in self.db.execute("SELECT DISTINCT language FROM lines"):
            self.languages.append(list(r)+[False])
        self.emit(SIGNAL("dataChanged()"))
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        language = self.languages[index.row()]
        if index.column()==0 and role==Qt.CheckStateRole:
            return language[1]
        if role!=Qt.DisplayRole: return None
        return language[index.column()]
    def flags(self, index):
        if not index.isValid(): return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
    def hasChildren(self, index):
        return False;
    def index(self, row, column, parent=QModelIndex()):
        if row>=len(self.languages) or row<0 or column<0 or column>2:
            return QModelIndex()
        return self.createIndex(row, column, self.languages[row]);
    def parent(self, index):
        return QModelIndex()
    def columnCount(self, parent=QModelIndex()):
        return 1
    def rowCount(self, parent=QModelIndex()):
        return len(self.languages)
    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid(): return False
        lang=self.languages[index.row()]
        if role==Qt.CheckStateRole:
            lang[1] = value
            # emit a signal and send a list of checked tags
            self.emit(
                SIGNAL("itemChecked(PyQt_PyObject)"),
                [lang[0] for lang in self.languages if lang[1]]
            )
            return True
        return False

class TaglinesModel(QAbstractItemModel): #{{{1
    """
    This model provides the taglines for the current filter settings.
    """
    def __init__(self, parent, database):
        QAbstractItemModel.__init__(self, parent)
        self.window = parent
        self.author = None
        self.languages = []
        self.tags = []
        self.setDB(database)
        self.setHeaderData(0, Qt.Horizontal, "ID",   Qt.DisplayRole)
        self.setHeaderData(1, Qt.Horizontal, "Author", Qt.DisplayRole)
        self.setHeaderData(2, Qt.Horizontal, "Source", Qt.DisplayRole)
        self.setHeaderData(3, Qt.Horizontal, "Remark", Qt.DisplayRole)
        self.setHeaderData(3, Qt.Horizontal, "Date", Qt.DisplayRole)
    def setDB(self, database):
        self.db = database
        self.beginResetModel()
        self.taglines = []
        self.endResetModel()
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        if role==Qt.TextAlignmentRole:
            return Qt.AlignRight if index.column()==0 else Qt.AlignLeft
        elif role!=Qt.DisplayRole: return None
        return self.taglines[index.row()][0][index.column()]
    def hasChildren(self, index):
        return not index.isValid();
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role==Qt.DisplayRole and orientation==Qt.Horizontal:
            return ("ID", "Author", "Source", "Remark", "Date")[section]
    def index(self, row, column, parent=QModelIndex()):
        if row>=len(self.taglines) or row<0 or column<0 or column>4:
            return QModelIndex()
        return self.createIndex(row, column, self.taglines[row]);
    def parent(self, index):
        return QModelIndex()
    def columnCount(self, parent=QModelIndex()):
        return 5
    def rowCount(self, parent=QModelIndex()):
        return len(self.taglines)
    def refresh(self):
        self.beginResetModel()
        self.taglines = []
        if self.db is None:
            self.endResetModel()
            return True
        # construct DB query based on filter settings
        # first, connect all taglines items with lines items
        query = """SELECT tl.id, a.name, tl.source, tl.remark, tl.date,
              l.id, l.date, l.language, l.text
              FROM taglines tl JOIN lines l ON tl.id=l.tagline
              LEFT JOIN authors a ON tl.author = a.id"""
        i = 1
        # filter for all selected tags with AND (TODO: implement OR option?)
        for tag in self.tags:
            tagx = "t"+str(i)
            query += " JOIN tag "+tagx+" ON "+tagx+".tag = "+tag+" AND "+tagx+".tagline = tl.id"
            i = i + 1
        # append WHERE clause...
        where = " WHERE "
        # for author
        if self.author and self.author > -2:
            query += where + "author=" + str(self.author)
            where = " AND "
        # and all selected languages
        if self.languages:
            query += where + "language IN ('" + "','".join(
                str(lang) for lang in self.languages) + "')"

        currentId = -1
        lines = []
        try:
            # go through all rows...
            for row in self.db.execute(query):
                id = row[0]
                # new tagline ID
                if id != currentId:
                    # we have some lines for the old ID -> store them
                    if lines:
                        self.taglines.append(lines)
                        lines = []
                    currentId = id
                    lines.append(row[:5])
                lines.append(row[5:])
            # add lines for the last ID of the loop
            if currentId != -1:
                self.taglines.append(lines)
        except sqlite3.OperationalError as e:
            # TODO: what to output?
            raise
        self.endResetModel()
    def setAuthor(self, author):
        if isinstance(author, int):
            if author == -2:
                self.author = None
            else:
                self.author = author
        else:
            self.author = None
        self.refresh()
    def setLanguages(self, languages):
        self.languages = languages
        self.refresh()
    def setTags(self, tags):
        self.tags = tags
        self.refresh()

class TagsModel(QAbstractItemModel): #{{{1
    """
    This class is the interface to the tags in the database

    It allows to select a number of tags for a tagline.
    """
    def __init__(self, parent):
        QAbstractItemModel.__init__(self, parent)
        self.parent = parent
        self.tags = []
        self.setHeaderData(0, Qt.Horizontal, "ID", Qt.DisplayRole)
        self.setHeaderData(1, Qt.Horizontal, "Name", Qt.DisplayRole)
    def add(self, tag):
        if tag=="" or not self.db: return False
        count = self.rowCount()
        self.beginInsertRows(QModelIndex(), count, count)
        c = self.db.cursor()
        c.execute("INSERT INTO tags (text) values (?)", (tag,))
        self.tags.append([c.lastrowid, tag, False])
        self.endInsertRows()
        self.emit(SIGNAL("rowsInserted()"))
        return True
    def set(self, index, newName):
        tag = self.tags[index.row()]
        tag[1] = newName
        self.db.execute("UPDATE tags SET text=? WHERE id=?", (tag[1], tag[0]))
        self.emit(SIGNAL("dataChanged(QModelIndex"), index)
        return True
    def delete(self, index):
        if not index.isValid(): return False
        tag = self.tags[index.row()][0]
        self.beginRemoveRows(QModelIndex(), index.row(), index.row())
        # delete all assignments to this tag
        self.db.execute("DELETE FROM tag WHERE tag=?", (tag,))
        # delete tag itself
        self.db.execute("DELETE FROM tags WHERE id=?", (tag,))
        self.tags[index.row():index.row()+1]=[]
        self.endRemoveRows()
        self.emit(SIGNAL("rowsDeleted()"))
        return True
    def setDB(self, db):
        self.db = db
        self.beginResetModel()
        self.tags=[]
        for r in self.db.execute("SELECT * FROM tags ORDER BY text"):
            self.tags.append(list(r)+[False])
        self.endResetModel()
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        tag = self.tags[index.row()]
        if index.column()==1 and role==Qt.CheckStateRole:
            return tag[2]
        if role!=Qt.DisplayRole: return None
        return tag[index.column()]
    def hasChildren(self, index):
        return False;
    def index(self, row, column, parent=QModelIndex()):
        if row>=len(self.tags) or row<0 or column<0 or column>2:
            return QModelIndex()
        return self.createIndex(row, column, self.tags[row]);
    def parent(self, index):
        return QModelIndex()
    def columnCount(self, parent=QModelIndex()):
        return 2
    def rowCount(self, parent=QModelIndex()):
        return len(self.tags)
    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid(): return False
        tag=self.tags[index.row()]
        if role==Qt.CheckStateRole:
            tag[2] = value
            # emit a signal and send a list of checked tags
            self.emit(
                SIGNAL("itemChecked(PyQt_PyObject)"),
                [str(tag[0]) for tag in self.tags if tag[2]]
            )
            return True
        return False
        if index.column()==1 and role==Qt.EditRole:
            text = unicode(value.toString()).strip()
            if tag[1]==text: return True
            tag[1] = text
            self.db.execute("UPDATE tags SET text = ? WHERE id = ?",
                (tag[1], tag[0]))
        self.emit(SIGNAL("dataChanged(QModelIndex"), index)
        return True

class TagProxyModel(QSortFilterProxyModel): #{{{1
    """
    This proxy sorts the tag data.
    """
    def __init__(self, parent, checkable = False):
        QSortFilterProxyModel.__init__(self, parent)
        self.checkable = checkable
        self.setDynamicSortFilter(True)
        self.sort(1, Qt.AscendingOrder)
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        index = self.mapToSource(index)
        if role==Qt.CheckStateRole:
            if self.checkable:
                return self.sourceModel().data(index, role)
            else:
                return None
        return self.sourceModel().data(index, role)
    def flags(self, index):
        if not index.isValid(): return Qt.NoItemFlags
        f = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if self.checkable and index.column()==1:
            f |= Qt.ItemIsUserCheckable
        return f

class TagDatabase(QObject): #{{{1
    """
    encapsulates access to the models and state information
    """
    def __init__(self):
        QObject.__init__(self, None)
        self.authors = AuthorModel(None)
        self.languages = LanguagesModel(None)
        self.tags = TagsModel(None)
        self.taglines = TaglinesModel(None, None)
        for model in (self.authors, self.tags):
            self.connect(model, SIGNAL("dataChanged()"), self.dataChanged)
            self.connect(model, SIGNAL("rowsInserted()"), self.dataChanged)
            self.connect(model, SIGNAL("rowsDeleted()"), self.dataChanged)
        self.connect(self.languages, SIGNAL("itemChecked(PyQt_PyObject)"), self.taglines.setLanguages)
        self.connect(self.tags, SIGNAL("itemChecked(PyQt_PyObject)"), self.taglines.setTags)
        self.db = None
        self.changed = False
    def active(self):
        return not self.db is None
    def changed(self):
        return changed
    def close(self):
        if self.active():
            if self.changed:
            # TODO: ask whether to save
                self.db.commit()
            self.db.close()
            db = None
        return True
    def dataChanged(self):
        self.changed = True
    def loadFromFile(self, url):
        if not self.close(): return False
        self.db = taglines.Database(url)
        self.authors.setDB(self.db)
        self.languages.setDB(self.db)
        self.tags.setDB(self.db)
        self.taglines.setDB(self.db)
        self.changed = False
        return True
    def authorsModel(self):
        return self.authors
    def languagesModel(self):
        return self.languages
    def tagsModel(self):
        return self.tags
    def taglinesModel(self):
        return self.taglines
    def getLines(self, tagline):
        query = "SELECT id, language, text FROM lines WHERE tagline = ?"
        lines = []
        for r in self.db.execute(query, (tagline,)):
            lines.append(r)
        return lines

class EditAuthorDialog(QDialog): #{{{1
    """
    This dialogue edits the data of one author
    """
    def __init__(self, parent, author):
        QDialog.__init__(self, parent, Qt.Dialog)
        self.author = author

        mainLayout = QGridLayout(self)
        mainLayout.addWidget(QLabel("Name:"), 0, 0, Qt.AlignRight)
        self.nameEdit = QLineEdit(parent)
        self.nameEdit.setMaxLength(255)
        self.nameEdit.setMinimumWidth(300)
        self.nameEdit.setText(author[1])
        mainLayout.addWidget(self.nameEdit, 0, 1)

        layout = QHBoxLayout()
        mainLayout.addWidget(QLabel("Born:"), 1, 0, Qt.AlignRight)
        self.bornDial = QSpinBox(self)
        self.bornDial.setRange(-4000, 4000)
        if not author[2] is None: self.bornDial.setValue(author[2])
        layout.addWidget(self.bornDial)
        layout.addStretch(1)
        layout.addWidget(QLabel("Died:"))
        self.diedDial = QSpinBox(self)
        self.diedDial.setRange(-4000, 4000)
        if not author[3] is None: self.diedDial.setValue(author[3])
        layout.addWidget(self.diedDial)
        layout.addStretch(1)
        mainLayout.addLayout(layout, 1, 1)

        layout = QHBoxLayout()
        layout.addStretch(1)
        okButton = QPushButton("&OK", self)
        okButton.setDefault(True)
        okButton.setIcon(QIcon.fromTheme("dialog-ok"))
        layout.addWidget(okButton)
        cancelButton = QPushButton("&Cancel", self)
        cancelButton.setIcon(QIcon.fromTheme("dialog-cancel"))
        layout.addWidget(cancelButton)
        mainLayout.addLayout(layout, 2, 1, Qt.AlignRight | Qt.AlignBottom)

        self.connect(okButton, SIGNAL('clicked()'), self.ok)
        self.connect(cancelButton, SIGNAL('clicked()'), self.reject)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    def ok(self):
        error = ""
        name = unicode(self.nameEdit.text())
        if name == "":
            error = "Please enter a name."
        born = self.bornDial.value()
        died = self.diedDial.value()
        if born>died and born!=0 and died!=0:
            error = "The year of birth must be lower than the year of death.\nEnter 0 to ignore a date."
        if error!="":
            QMessageBox.critical(self, "Data invalid", error)
        else:
            self.author[1:]=[name,
                born if born!=0 else None,
                died if died!=0 else None]
            self.accept()

class EditAuthorsDialog(QDialog): #{{{1
    """
    This dialogue manages the list of authors
    """
    def __init__(self, parent, database):
        QDialog.__init__(self, parent)
        self.model = database.authorsModel()
        self.proxyModel = AuthorProxyModel(self)
        self.proxyModel.setSourceModel(self.model)
        self.setWindowTitle("Manage Tagline Authors")

        mainLayout = QHBoxLayout(self)
        self.authors = QTreeView(self)
        self.authors.setModel(self.proxyModel)
        self.authors.setRootIsDecorated(False)
        self.authors.hideColumn(0)
        header = self.authors.header()
        header.setResizeMode(1, QHeaderView.Stretch)
        header.setResizeMode(2, QHeaderView.ResizeToContents)
        header.setResizeMode(3, QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)

        addButton = QPushButton("&Add", self)
        self.editButton = QPushButton("&Edit", self)
        self.delButton = QPushButton("&Delete", self)
        closeButton = QPushButton("&Close", self)
        addButton.setIcon(QIcon.fromTheme("list-add"))
        self.editButton.setIcon(QIcon.fromTheme("document-edit"))
        self.delButton.setIcon(QIcon.fromTheme("edit-delete"))
        closeButton.setIcon(QIcon.fromTheme("dialog-ok"))

        buttonLayout = QVBoxLayout()
        buttonLayout.addWidget(addButton)
        buttonLayout.addWidget(self.editButton)
        buttonLayout.addWidget(self.delButton)
        buttonLayout.addStretch(1)
        buttonLayout.addWidget(closeButton)

        mainLayout.addWidget(self.authors)
        mainLayout.addLayout(buttonLayout)
        self.resize(QSize(480,480))
        self.connect(addButton, SIGNAL('clicked()'), self.addAuthor)
        self.connect(self.editButton, SIGNAL('clicked()'), self.editSelectedAuthor)
        self.connect(self.delButton, SIGNAL('clicked()'), self.deleteSelectedAuthor)
        self.connect(closeButton, SIGNAL('clicked()'), self.close)
        self.editButton.setEnabled(False)
        self.delButton.setEnabled(False)

        selectionModel = self.authors.selectionModel()
        self.connect(selectionModel,
            SIGNAL('selectionChanged(QItemSelection, QItemSelection)'),
            self.selectionChanged)
        self.connect(self.authors,
                SIGNAL('doubleClicked(QModelIndex)'),
                self.authorDoubleClicked)
    def selectionChanged(self, selected, deselected):
        enabled = len(selected.indexes())!=0
        self.editButton.setEnabled(enabled)
        self.delButton.setEnabled(enabled)
    def addAuthor(self):
        author = [-1, "", None, None]
        dlg = EditAuthorDialog(self, author)
        if dlg.exec_():
            self.model.add(author)
    def editSelectedAuthor(self):
        selection = self.authors.selectionModel().selectedRows(1)
        if len(selection)==0: return False
        self.editAuthorByIndex(self.proxyModel.mapToSource(selection[0]))
    def deleteSelectedAuthor(self):
        selection = self.authors.selectionModel().selectedRows(1)
        if len(selection)==0: return False
        button = QMessageBox.question(self,
            "Delete Author",
            "Do you also want to delete all taglines by that author?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Cancel
        )
        if button==QMessageBox.Cancel:
            return False
        self.model.delete(
            self.proxyModel.mapToSource(selection[0]),
            button==QMessageBox.Yes)
        return True
    def authorDoubleClicked(self, index):
        if index.isValid():
            self.editAuthorByIndex(self.proxyModel.mapToSource(index))
    def editAuthorByIndex(self, index):
        author = self.model.get(index)
        dlg = EditAuthorDialog(self, author)
        if dlg.exec_():
            self.model.set(author)
            self.proxyModel.sort(1, Qt.AscendingOrder)


class EditTagsDialog(QDialog): #{{{1
    """
    This dialogue manages the list of tags
    """
    def __init__(self, parent, database):
        QDialog.__init__(self, parent)
        self.model = database.tagsModel()
        self.setWindowTitle("Manage Tagline Tags")

        mainLayout = QHBoxLayout(self)
        layout = QVBoxLayout()

        self.newName = QLineEdit(self)
        self.newName.setMaxLength(50)
        self.connect(self.newName, SIGNAL('textChanged(QString)'), self.newNameChanged)
        #self.connect(self.newName, SIGNAL('returnPressed()'), self.addTag)
        layout.addWidget(self.newName)

        self.tags = QListView(self)
        self.proxy = TagProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.tags.setModel(self.proxy)
        self.tags.setModelColumn(1)
        layout.addWidget(self.tags)
        mainLayout.addLayout(layout)

        self.addButton = QPushButton("&Add", self)
        self.editButton = QPushButton("&Rename", self)
        self.delButton = QPushButton("&Delete", self)
        closeButton = QPushButton("&Close", self)
        self.addButton.setIcon(QIcon.fromTheme("list-add"))
        self.editButton.setIcon(QIcon.fromTheme("document-edit"))
        self.delButton.setIcon(QIcon.fromTheme("edit-delete"))
        closeButton.setIcon(QIcon.fromTheme("dialog-ok"))

        buttonLayout = QVBoxLayout()
        buttonLayout.addWidget(self.addButton)
        buttonLayout.addWidget(self.editButton)
        buttonLayout.addWidget(self.delButton)
        buttonLayout.addStretch(1)
        buttonLayout.addWidget(closeButton)
        mainLayout.addLayout(buttonLayout)

        self.resize(QSize(320,480))
        self.addButton.setEnabled(False)
        self.editButton.setEnabled(False)
        self.delButton.setEnabled(False)
        self.connect(self.addButton, SIGNAL('clicked()'), self.addTag)
        self.connect(self.editButton, SIGNAL('clicked()'), self.editTag)
        self.connect(self.delButton, SIGNAL('clicked()'), self.deleteTag)
        self.connect(closeButton, SIGNAL('clicked()'), self.close)

        selectionModel = self.tags.selectionModel()
        self.connect(selectionModel,
            SIGNAL('selectionChanged(QItemSelection, QItemSelection)'),
            self.selectionChanged)
    def newNameChanged(self, text):
        selection = self.tags.selectionModel().currentIndex()
        self.addButton.setEnabled(text!="")
        self.editButton.setEnabled(text!="" and selection.isValid())
    def selectionChanged(self, selected, deselected):
        enabled = len(selected.indexes())!=0
        if enabled:
            self.newName.setText(
                self.model.data(
                    self.proxy.mapToSource(selected.indexes()[0])
            ))
        self.addButton.setEnabled(False)
        self.editButton.setEnabled(False)
        self.delButton.setEnabled(enabled)
    def addTag(self):
        tag = unicode(self.newName.text())
        if self.model.match(
                self.model.index(0,1), Qt.DisplayRole,
                tag, 1, Qt.MatchExactly):
            QMessageBox.critical(self, "Could not add tag",
                "A tag of this name already exists.")
            return False
        else:
            self.model.add(tag)
            self.newName.setText("")
            return True
    def editTag(self):
        selection = self.tags.selectionModel().currentIndex()
        if not selection.isValid(): return False
        tag = self.model.data(self.model.index(selection.row(),1), Qt.DisplayRole)
        newName = self.newName.text()
        if tag==newName:
            QMessageBox.critical(self, "Could not rename tag",
                "Old and new name are the same.")
            return False
        if self.model.match(
                self.model.index(0,1), Qt.DisplayRole,
                newName, 1, Qt.MatchExactly):
            QMessageBox.critical(self, "Could not rename tag",
                "A tag of this name already exists.")
            return False
        self.model.set(selection, unicode(newName))
    def deleteTag(self):
        selection = self.tags.selectionModel().currentIndex()
        if not selection.isValid(): return False
        button = QMessageBox.question(self,
            "Delete Tag",
            "Do you really want to delete the tag and all assignments to it?",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if button==QMessageBox.Cancel:
            return False
        self.model.delete(self.proxy.mapToSource(selection))
        return True

class TaglinesWindow(QMainWindow): #{{{1
    def __init__(self, path=None): #{{{2
        QMainWindow.__init__(self)
        self.resize(800,600)
        self.setWindowTitle('Taglines database')
        self.database = TagDatabase()

        # Create actions
        newAction = QAction('New database', self)
        openAction = QAction('Open database', self)
        saveAction = QAction('Save database', self)
        saveAsAction = QAction('Save database as', self)
        exitAction = QAction('Exit', self)
        editAuthorsAction = QAction('Edit Authors...', self)
        editTagsAction = QAction('Edit Tags...', self)
        editAction = QAction('Edit Phrase Pairs', self)
        refreshAction = QAction('Refresh View', self)

        newAction.setShortcut('Ctrl+N')
        openAction.setShortcut('Ctrl+O')
        saveAction.setShortcut('Ctrl+S')
        saveAsAction.setShortcut('Ctrl+Shift+S')
        editAuthorsAction.setShortcut('Ctrl+U')
        editTagsAction.setShortcut('Ctrl+T')
        exitAction.setShortcut('Ctrl+Q')
        refreshAction.setShortcut('Ctrl+R')

        newAction.setIcon(QIcon.fromTheme("document-new"))
        openAction.setIcon(QIcon.fromTheme("document-open"))
        saveAction.setIcon(QIcon.fromTheme("document-save"))
        saveAsAction.setIcon(QIcon.fromTheme("document-save-as"))
        exitAction.setIcon(QIcon.fromTheme("application-exit"))
        refreshAction.setIcon(QIcon.fromTheme("view-refresh"))

        # Create menubar with actions
        menubar = self.menuBar()
        filemenu = menubar.addMenu('&File')
        filemenu.addAction(newAction)
        filemenu.addAction(openAction)
        filemenu.addSeparator()
        filemenu.addAction(saveAction)
        filemenu.addAction(saveAsAction)
        filemenu.addSeparator()
        filemenu.addAction(exitAction)
        editmenu = menubar.addMenu('&Edit')
        editmenu.addAction(editAuthorsAction)
        editmenu.addAction(editTagsAction)
        editmenu.addSeparator()
        editmenu.addAction(refreshAction)

        mainSplitter = QSplitter(Qt.Horizontal, self)
        rightSplitter = QSplitter(Qt.Vertical, self)
        sidebarSplitter = QSplitter(Qt.Vertical, self)

        # filter widgets at left edge
        sidebar = QWidget()
        sidebarLayout = QVBoxLayout()
        sidebar.setLayout(sidebarLayout)

        # author filter
        sidebarLayout.addWidget(QLabel('Author:'))
        self.AuthorList = QComboBox()
        proxy = AuthorProxyModel(self, True)
        proxy.setSourceModel(self.database.authorsModel())
        self.AuthorList.setModel(proxy)
        self.AuthorList.setModelColumn(1)
        self.AuthorList.setCurrentIndex(0)
        sidebarLayout.addWidget(self.AuthorList)

        # languages filter
        sidebarLayout.addWidget(QLabel('Languages:'))
        self.LangList = QListView()
        self.LangList.setModel(self.database.languagesModel())
        self.LangList.setModelColumn(1)
        sidebarLayout.addWidget(self.LangList)

        sidebarSplitter.addWidget(sidebar)

        sidebar = QWidget()
        sidebarLayout = QVBoxLayout()
        sidebar.setLayout(sidebarLayout)

        # tags filter
        sidebarLayout.addWidget(QLabel('Tags:'))
        self.TagList = QListView()
        proxy = TagProxyModel(self, True)
        proxy.setSourceModel(self.database.tagsModel())
        self.TagList.setModel(proxy)
        self.TagList.setModelColumn(1)
        sidebarLayout.addWidget(self.TagList)

        sidebarSplitter.addWidget(sidebar)
        mainSplitter.addWidget(sidebarSplitter)

        sidebarSplitter.setStretchFactor(0, 0)
        sidebarSplitter.setStretchFactor(1, 1)

        # main views
        self.TaglinesWidget = QTreeView(self)
        self.TaglinesWidget.setModel(self.database.taglinesModel())
        header = self.TaglinesWidget.header()
        header.setResizeMode(0, QHeaderView.ResizeToContents)
        header.setResizeMode(1, QHeaderView.Interactive)
        header.setResizeMode(2, QHeaderView.Interactive)
        header.setResizeMode(3, QHeaderView.Interactive)
        header.setResizeMode(4, QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        self.LinesWidget = QTreeWidget(self)
        rightSplitter.addWidget(self.TaglinesWidget)
        rightSplitter.addWidget(self.LinesWidget)
        rightSplitter.setStretchFactor(0, 1)
        rightSplitter.setStretchFactor(1, 0)

        mainSplitter.addWidget(rightSplitter)
        mainSplitter.setStretchFactor(0, 0)
        mainSplitter.setStretchFactor(1, 1)
        self.setCentralWidget(mainSplitter)

        # Connect everything
        # actions
        #self.connect(newAction, SIGNAL('triggered()'), self.newFile)
        self.connect(openAction, SIGNAL('triggered()'), self.openFile)
        #self.connect(saveAction, SIGNAL('triggered()'), self.saveFile)
        #self.connect(saveAsAction, SIGNAL('triggered()'), self.saveFileAs)
        self.connect(exitAction, SIGNAL('triggered()'), SLOT('close()'))
        self.connect(editAuthorsAction, SIGNAL('triggered()'), self.editAuthors)
        self.connect(editTagsAction, SIGNAL('triggered()'), self.editTags)
        self.connect(refreshAction, SIGNAL('triggered()'), self.database.taglinesModel().refresh)

        # widgets
        # send changed author selection to taglines view
        self.connect(
            # TODO: activated richtig?
            self.AuthorList, SIGNAL('activated(int)'),
            self.authorSelectionChanged)
        # change of selection in main view
        selectionModel = self.TaglinesWidget.selectionModel()
        self.connect(selectionModel,
            SIGNAL('selectionChanged(QItemSelection, QItemSelection)'),
            self.taglineSelectionChanged)
        self.connect(self.TaglinesWidget,
                SIGNAL('doubleClicked(QModelIndex)'),
                self.taglineDoubleClicked)

        if path: self.loadFile(path)
        #}}}3

    def closeEvent(self, event):
        event.accept() if self.database.close() else event.ignore()
    def editAuthors(self):
        dialog = EditAuthorsDialog(self, self.database)
        dialog.exec_()
    def editTags(self):
        dialog = EditTagsDialog(self, self.database)
        dialog.exec_()
    def loadFile(self, url):
            if not self.database.close():
                return False
            try:
                self.database.loadFromFile(str(url))
                self.AuthorList.setCurrentIndex(0)
            #except InvalidFileError:
            #    QMessageBox.warning(None, "Error", "This file is not a taglines database.")
            #    return False
            except IOError:
                QMessageBox.critical(self, "Error", "An error occured while reading the file.")
                return False
            return True
    def openFile(self):
        # TODO: if self.changed: ask to save
        if kde:
            url = QFileDialog.getOpenFileName(
                self, 'Open a taglines database', '',
                'SQLite-Database (*.sqlite)\n*.*|All Files')
        else:
            url = KFileDialog.getOpenFileName(
                KUrl(), 'SQLite-Database (*.sqlite)\n*.*|All Files',
                self, 'Open a taglines database')

        if url!='':
            self.loadFile(url)
    def refresh(self):
        self.TaglinesWidget.model().refresh()
    def authorSelectionChanged(self, index):
        model = self.AuthorList.model()
        data = model.data(model.index(index, 0))
        self.database.taglinesModel().setAuthor(data)
    def taglineSelectionChanged(self, selected, deselected):
        enabled = len(selected.indexes())!=0
        if enabled:
            # selected row, column 0
            index = selected.indexes()[0]
            id = self.database.taglinesModel().data(index)
            lines = self.database.getLines(id)
            print(lines)
            self.LinesWidget.clear()
#                self.model.data(
#                    self.proxy.mapToSource(selected.indexes()[0])
#                ))
    def taglineDoubleClicked(self, index):
        pass
#}}}1
