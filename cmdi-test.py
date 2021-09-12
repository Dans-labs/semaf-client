#!/usr/bin/python3

from xml.dom import minidom
from CLARIAH_CMDI.xml2dict.processor import CMDI # load, xmldom2dict
import json
from config import cmdifile, ROOT, DATAVERSE_ID, API_TOKEN
from Semaf import Semaf
from jGraph import jGraph
import sys

sm = Semaf()
cmdifile = sys.argv[1:] 
s = sm.loadcmdi(cmdifile[0])
cwfile = "test-cmdi-crosswalks.csv"

cmdigraph = jGraph(sm.json, "https://dataverse.org/schema/cmdi/")
cmdigraph.load_crosswalks(cwfile)
cmdigraph.rotate(cmdigraph.context, False)
cmdigraph.g.serialize(format='json-ld', destination='/tmp/maincmdi.jsonld')
cmdigraph.g.serialize(format='n3', destination='/tmp/Xcmdi.nt')
cmdigraph.g.serialize(format='xml', destination='/tmp/Xcmdi.rdf')

sm.loadjson(cmdigraph.g.serialize(format='json-ld'), 'json-ld')
print(sm.dumps(True))

# Write jsonld to file and ingest in Dataverse
outfile = '/tmp/curlexample'
open(outfile, 'w').write(sm.dumps(True))
print(cmdigraph.dataset_upload(ROOT, DATAVERSE_ID, API_TOKEN, outfile))
#print(json.dumps(cmdigraph.crosswalks, indent=2))
