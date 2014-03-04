# -*- coding: utf-8 -*-
'''
Object explorer in PySide/PyQt4
Created on May 07 2013

@author: Christopher Liman
Features:
represents the following categories of objects in globals() or a root object as a tree:
- sequence-like objects (e.g. lists, numpy arrays)
- mapping-like objects (e.g. dicts, pandas objects)
- classes/instances with __dict__ not from a module
- classes/instances with __dict__ from a module
- other objects
copy names of objects to clipboard
natural sorting of tree
circular references detection
Todo:
auto refresh
don't block the terminal even when not running in IPython
'''

from __future__ import nested_scopes, generators, division, absolute_import, with_statement, print_function, unicode_literals
import numpy as np
import pandas as pd
#import sip
import sys
from copy import copy
from re import split
#from functools import partial
from spyderlib.qt import QtGui
#from PyQt4 import QtGui
#from PyQt4 import QtCore
from IPython.lib import guisupport
import objectexplorer_ui

#assert sip.getapi('QString') == 2


class ObjectExplorer(QtGui.QMainWindow, objectexplorer_ui.Ui_ObjectExplorer):
    '''Object explorer'''
    def __init__(self, parent=None):
        super(ObjectExplorer, self).__init__(parent)  # boilerplate
        self.setupUi(self)  # boilerplate
        self.pushButton.clicked.connect(self.add_root)
        self.actionCopy_path.triggered.connect(self.copy_path)
        #self.actionExit.triggered.connect(partial(self.closeEvent, QtGui.QCloseEvent()))  # use partial to pass argument to slot
        self.actionExit.triggered.connect(self.close)
        self.treeWidget.addAction(self.actionCopy_path)  # adds action to treeWidget's right click menu

    def add_root(self):
        '''clear tree and add root object'''
        root_path = self.lineEdit_rootObject.text()
        if root_path == '':  # if blank, browse globals
            root_obj = None
            (root_dict, root_cat) = (globals(), 'globals')
        else:
            try:
                root_obj = reduce(getattr, str(root_path).split('.'), sys.modules[__name__])
                # http://stackoverflow.com/questions/1176136/convert-string-to-python-class-object
                # to do: let root be an element such as item[0]
            except AttributeError:
                self.statusBar().showMessage('Invalid root object')
                return
            (root_dict, root_cat) = self.get_dict(root_obj)
        self.treeWidget.setSortingEnabled(False)
        self.treeWidget.clear()
        self.treeWidget.addTopLevelItem(TreeWidgetItem())  # add root to tree
        index = self.treeWidget.topLevelItemCount() - 1
        root_item = self.treeWidget.topLevelItem(index)
        self.set_text(root_item, root_path, root_obj, root_cat)  # adds text to each column
        root_item.setToolTip(0, root_path)  # add tooltip
        self.statusBar().showMessage('')
        root_item.setExpanded(1)
        if root_cat != 'other':
            self.add_subitems(root_dict, root_item, root_path, root_cat, [root_obj])  # if it has dict, add child items to tree
        self.treeWidget.setSortingEnabled(True)

    def add_subitems(self, dict_to_tree, QTreeWidgetItem_parent, parent_path, parent_cat, obj_chain):
        '''add items in dict to tree'''
        counter = 0
        if len(obj_chain) > self.spinBox_depth.value():
            self.statusBar().showMessage('Depth exceeded')
            return
        for (key, value) in dict_to_tree.items():
            (current_dict, current_cat) = self.get_dict(value)  # get subitem's dict
            if current_cat == 'mapping' and self.checkBox_mapping.isChecked() is False:
                continue
            elif current_cat == 'sequence' and self.checkBox_sequence.isChecked() is False:
                continue
            elif current_cat == 'mainobject' and self.checkBox_mainobject.isChecked() is False:
                continue
            elif current_cat == 'moduleobject' and self.checkBox_moduleobject.isChecked() is False:
                continue
            elif current_cat == 'other' and self.checkBox_other.isChecked() is False:
                continue
            counter += 1
            if counter > self.spinBox_length.value():
                return
            QTreeWidgetItem_parent.addChild(TreeWidgetItem())
            index = QTreeWidgetItem_parent.childCount() - 1
            current_item = QTreeWidgetItem_parent.child(index)
            self.set_text(current_item, key, value, current_cat)  # adds text to each column
            current_path = self.get_path(key, parent_cat, parent_path)
            current_item.setToolTip(0, current_path)  # add tooltip
            if current_cat != 'other' and any(item is value for item in obj_chain):  # detect circular references
                #current_item.setTextColor(0, QtGui.QColor(255, 0, 0))
                current_item.setForeground(0, QtGui.QColor(255, 0, 0))
                self.statusBar().showMessage('Circular reference detected: ' + str(value))
            elif current_cat != 'other':
                obj_chain_new = copy(obj_chain)
                obj_chain_new.append(value)
                self.add_subitems(current_dict, current_item, current_path, current_cat, obj_chain_new)  # if it has dict, add child items to tree

    def get_dict(self, obj):
        '''get item's dict and category'''
        if isinstance(obj, dict):
            dict_to_tree = obj
            item_cat = 'mapping'
        elif isinstance(obj, (pd.Series, pd.DataFrame, pd.Panel)):
            dict_to_tree = dict(obj)
            item_cat = 'mapping'
        elif isinstance(obj, np.matrix) and np.all(dict(enumerate(obj))[0] == obj):
            dict_to_tree = None  # fix for np.matrix infinite sets of indices
            item_cat = 'other'
        elif hasattr(obj, '__getitem__') and hasattr(obj, '__len__') and not isinstance(obj, basestring):
            try:
                if len(obj) > 0:
                    dict_to_tree = dict(enumerate(obj))  # list, tuple, bytearray, np.ndarray
                    item_cat = 'sequence'
                else:
                    (dict_to_tree, item_cat) = self.get_dict2(obj)
            except:
                (dict_to_tree, item_cat) = self.get_dict2(obj)
        else:
            (dict_to_tree, item_cat) = self.get_dict2(obj)
        return (dict_to_tree, item_cat)

    def get_dict2(self, obj):
        if hasattr(obj, '__dict__') and (getattr(obj, '__module__', False) == '__main__'):
            dict_to_tree = obj.__dict__  # objects with __dict__ not from a module
            item_cat = 'mainobject'
        elif hasattr(obj, '__dict__'):
            dict_to_tree = obj.__dict__  # objects with __dict__ from a module
            item_cat = 'moduleobject'
        else:
            dict_to_tree = None
            item_cat = 'other'
        return (dict_to_tree, item_cat)

    def get_path(self, item_key, parent_cat, parent_path):
        '''get string of item's full path/name'''
        if parent_path == '':
            item_path = str(item_key)
        elif parent_cat == 'moduleobject' or parent_cat == 'mainobject':
            item_path = parent_path + '.' + str(item_key)
        elif isinstance(item_key, str):
            item_path = parent_path + '[\'' + item_key + '\']'
        else:
            item_path = parent_path + '[' + str(item_key) + ']'
        return item_path

    def set_text(self, current_item, key, value, cat):
        '''adds text to each column for a given item'''
        current_item.setText(0, str(key))  # key
        current_item.setText(1, str(type(value)))  # type
        current_item.setText(2, str(cat))  # category
        if isinstance(value, np.ndarray):
            current_item.setText(3, str(np.shape(value)))  # shape
        elif hasattr(value, '__len__'):
            try:
                current_item.setText(3, str(len(value)))
            except:
                current_item.setText(3, str('none'))
        else:
            current_item.setText(3, str('none'))
        valuestring = repr(value)  # value
        if valuestring.count('\n') > 3:  # truncate after 3 lines
            valuestring = '\n'.join(valuestring.split('\n')[0:3]) + '\n...'
        current_item.setText(4, valuestring)
        if self.checkBox_expandAll.isChecked():
            current_item.setExpanded(1)

    def copy_path(self):
        '''Copies paths of selected items in treeWidget to clipboard'''
        clipboard = QtGui.QApplication.clipboard()
        clipboard_text = ', '.join([item.toolTip(0) for item in self.treeWidget.selectedItems()])
        clipboard.setText(clipboard_text)

#    def closeEvent(self, closeevent):
#        '''Note: special method name'''
#        reply = QtGui.QMessageBox.question(self, 'Message', 'Are you sure to quit?',
#                                           buttons=QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, defaultButton=QtGui.QMessageBox.No)
#        if reply == QtGui.QMessageBox.Yes:
#            closeevent.accept()
#            print('Closed')
#            #app.quit()
#        else:
#            closeevent.ignore()


class TreeWidgetItem(QtGui.QTreeWidgetItem):
    '''override __lt__ for natural sorting in treewidgets'''
    def __init__(self, parent=None):
        QtGui.QTreeWidgetItem.__init__(self, parent)

    def __lt__(self, other_item):
        column = self.treeWidget().sortColumn()
        return self.alphanum_key(str(self.text(column))) < self.alphanum_key(str(other_item.text(column)))

    # http://www.codinghorror.com/blog/2007/12/sorting-for-humans-natural-sort-order.html
    def convert(self, text):
        if text.isdigit():
            return int(text)
        else:
            return text.lower()

    def alphanum_key(self, key):
        return [self.convert(c) for c in split('([0-9]+)', key)]


if __name__ == '__main__':
    class EmptyClass(object):
        '''Example class to show browsing of instance objects in object explorer'''
        def __init__(self):
            pass

    my_namespace = EmptyClass()
    my_namespace.a = 'Hello'
    my_namespace.b = ['a3', '1', '5', '11', '20', 'a1', 'a10']  # list to sort
    my_namespace.bb = {'ArithmeticError': ArithmeticError, 'str': str}
    my_namespace.cc = {'z': np.array([[1, 'a'], [2, {'z': 3, 'y': 9}]]), 'y': {'z': 3, 'y': 9}}  # nested items
    my_namespace.c = {'y': EmptyClass(), 5: 'q', (4, 5): 't'}  # different keys for dict
    my_namespace.c['y'].z = [1, 2, 3]
    my_namespace.c['y'].y = 4
    my_namespace.c['y'].x = my_namespace.c  # circular reference
    my_namespace.d = np.matrix(b'[11,12,13;14,15,16;17,18,19]')
    my_namespace.e = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    my_namespace.s = pd.Series(np.random.randn(5), index=['a', 'b', 'c', 'd', 'e'])
    my_namespace.df = pd.DataFrame({'one': my_namespace.s, 'two': my_namespace.s})
    my_namespace.n = 8
    my_namespace.o = bytearray(b'hello')
    app = guisupport.get_app_qt4()
    #app = QtGui.QApplication(sys.argv)
    form = ObjectExplorer()
    form.show()
    guisupport.start_event_loop_qt4(app)  # doesn't block terminal when run in ipython
    #app.exec_()
