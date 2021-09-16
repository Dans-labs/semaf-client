#!/usr/bin/python3

from xml.dom import minidom
from CLARIAH_CMDI.xml2dict.processor import CMDI # load, xmldom2dict
import json
from config import cmdifile, ROOT, DATAVERSE_ID, API_TOKEN
from Semaf import Semaf
from jGraph import jGraph
import sys
import requests
from datetime import datetime

sm = Semaf()
cmdifile = sys.argv[1:] 
s = sm.loadcmdi(cmdifile[0])
DEPOSIT = True
cwfile = "test-cmdi-crosswalks.csv"

#cmdigraph = jGraph(sm.json, "https://dataverse.org/schema/cmdi/")
cmdigraph = jGraph(sm.json, "https://dataverse.org/schema/cbs/")
cmdigraph.load_crosswalks(cwfile)
cmdigraph.rotate(cmdigraph.context, False)
outputfile = "cbs"
cmdigraph.g.serialize(format='json-ld', destination="/tmp/%s.jsonld" % outputfile)
cmdigraph.g.serialize(format='n3', destination="/tmp/%s.nt" % outputfile)
cmdigraph.g.serialize(format='xml', destination="/tmp/%s.rdf" % outputfile)
cmdigraph.g.serialize(format='turtle', destination="/tmp/%s.ttl" % outputfile)

sm.loadjson(cmdigraph.g.serialize(format='json-ld'), 'json-ld')
print(sm.dumps(True))

# Write jsonld to file and ingest in Dataverse
outfile = '/tmp/curlexample'
open(outfile, 'w').write(sm.dumps(True))

if DEPOSIT:
    dataset = json.loads(cmdigraph.dataset_upload(ROOT, DATAVERSE_ID, API_TOKEN, outfile))
    if 'data' in dataset:
        doi = dataset['data']['persistentId'] 
        url_pid = "%s/api/datasets/:persistentId/add?persistentId=%s&key=%s" % (ROOT, doi, API_TOKEN)
        f1 = 'Xcmdi.nt'
        file_content = 'content2: %s' % datetime.now()
        with open('/tmp/Xcmdi.nt') as f:
            filecontent = f.read()
        files = {'file': (f1, filecontent) }
        params = {}
        params_as_json_string = json.dumps(params)

        payload = dict(jsonData=params_as_json_string)
        r = requests.post(url_pid, data=payload, files=files)
        print(r.text)
#print(json.dumps(cmdigraph.crosswalks, indent=2))
