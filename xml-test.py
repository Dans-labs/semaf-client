import json
import os
import sys
import requests
from datetime import datetime

from config import ROOT, DATAVERSE_ID, API_TOKEN
from Semaf import Semaf
from jGraph import jGraph

wd = os.getcwd()
sm = Semaf()
cmdifile = sys.argv[1:]
sm.loadcmdi(cmdifile[0])
DEPOSIT = False
cwfile = "odissei-cbs-crosswalks.csv"
# outputfile = 'cbs'
outputfile = os.path.splitext(os.path.basename(cmdifile[0]))[0]
output_folder = 'output'
n3_folder = 'rdf_output'

cmdigraph = jGraph(sm.json, f'https://dataverse.org/schema/{outputfile}/')
cmdigraph.load_crosswalks(cwfile)
cmdigraph.rotate(cmdigraph.context, False)
# cmdigraph.g.serialize(format='json-ld', destination=os.path.join(wd, output_folder, f'{outputfile}.jsonld'))
# cmdigraph.g.serialize(format='n3', destination=os.path.join(wd, output_folder, f'{outputfile}.nt'))
# cmdigraph.g.serialize(format='xml', destination=os.path.join(wd, output_folder, f'{outputfile}.rdf'))
# cmdigraph.g.serialize(format='turtle', destination=os.path.join(wd, output_folder, f'{outputfile}.ttl'))

sm.loadjson(cmdigraph.g.serialize(format='json-ld'), 'json-ld')
# print(sm.dumps(True))

# Write jsonld and n3 to file ...
upload_file = os.path.join(wd, output_folder, f'{outputfile}.jsonld')
n3_file     = os.path.join(wd, n3_folder, f'{outputfile}.n3')

open(upload_file, 'w').write(sm.dumps(True))
open(n3_file, 'w').write(sm.graph_to_turtle())

# ... and ingest in Dataverse:
if DEPOSIT:
    dataset = json.loads(cmdigraph.dataset_upload(ROOT, DATAVERSE_ID, API_TOKEN, upload_file))
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
