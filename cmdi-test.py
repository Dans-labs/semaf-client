#!/usr/bin/python3

from xml.dom import minidom
from CLARIAH_CMDI.xml2dict.processor import CMDI # load, xmldom2dict
import json
from config import cmdifile

actions = {}
cmdi = CMDI(actions)
d = cmdi.load(cmdifile)
jsonobj = json.dumps(cmdi.json['#document'], indent=2)
print(jsonobj)
