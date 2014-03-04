objectexplorer
===========

A GUI containing a tree view of the following categories of objects in globals() or a root object:
- sequence-like objects (e.g. lists, numpy arrays)
- mapping-like objects (e.g. dicts, pandas objects)
- classes/instances with __dict__ not from a module
- classes/instances with __dict__ from a module
- other objects

Leave the root object blank to display the objects in globals().

Features:
- copy names of objects to clipboard
- natural sorting of tree
- circular references detection

Todo:
- auto refresh
- don't block the terminal even when not running in IPython

I previously submitted an older version of this script as an enhancement to the Spyder IDE at [https://code.google.com/p/spyderlib/issues/detail?id=558].