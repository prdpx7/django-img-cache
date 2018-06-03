"""
To maintain compatibility b/w py2 & py3
"""
import sys
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
if PY2:
    from urllib import urlopen
elif PY3:
    from urllib.request import urlopen