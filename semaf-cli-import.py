from xml.dom import minidom
import os
import tempfile
#from CLARIAH_CMDI.xml2dict.processor import CMDI # load, xmldom2dict
import json
from SchemaLOD import Schema, GraphBuilder
from SemafCLI import SemafUtils
from config import default_crosswalks_location, crosswalks_location, cbs_default_crosswalks
from rdflib import Graph, URIRef, Literal, BNode, plugin, Namespace
from rdflib.serializer import Serializer
from rdflib.namespace import RDF, RDFS
#from config import cmdifile, ROOT, DATAVERSE_ID, API_TOKEN, schemaURL, cv_server, cwfile
from config import *
from Semaf import Semaf
from jGraph import jGraph
import sys
import requests
from datetime import datetime
from pathlib import Path

outputdir = tempfile.mkdtemp(suffix=None, prefix="semafoutput")

UPLOAD = False
if len(sys.argv) > 1:
    cmdifile = sys.argv[1]
    output_file_name = os.path.basename(cmdifile)
    if len(sys.argv) > 2:
        UPLOAD = True
else:
    print("XML file required as input parameter")
    exit()
    #cmdifile = '0b01e4108004e49d_INV_REG_REPARATIE_CONSUMENTENARTIKELEN_HANDEL_2008-01-01.dsc'


# Load citation block
Path(outputdir + "/citation").mkdir(parents=False, exist_ok=True)
semafcli = SemafUtils(cbs_default_crosswalks, crosswalks_location)
semafcli.set_nt_filename(outputdir + "/citation/" + "%s.nt" % output_file_name)
semafcli.set_semaf_filename(outputdir + "/citation/" + "%s.json" % output_file_name)
semafcli.set_semaf_filename_orig(outputdir + "/citation/" + "%s-orig.json" % output_file_name)
semafcli.set_schema(schema_name='citation', schema_URL=schemaURL)
semafcli.transformation(cmdifile, UPLOAD=UPLOAD)
metadata = semafcli.cmdigraph.dataset

# Load all other blocks
for schema_name in schemes:    
    Path(outputdir + "/" + schema_name).mkdir(parents=False, exist_ok=True)
    custom_semafcli = SemafUtils(cbs_default_crosswalks, crosswalks_location)
    custom_semafcli.set_nt_filename(outputdir + "/" + schema_name +"/" + "%s.nt" % output_file_name)
    custom_semafcli.set_semaf_filename(outputdir + "/" + schema_name +"/" + "%s.json" % output_file_name)
    custom_semafcli.set_semaf_filename_orig(outputdir + "/" + schema_name +"/" + "%s-orig.json" % output_file_name)
    custom_semafcli.set_schema(schema_name=schema_name, schema_URL=schemes[schema_name])
    custom_semafcli.transformation(cmdifile, UPLOAD=UPLOAD)
    if custom_semafcli.cmdigraph.dataset:
        metadata['datasetVersion']['metadataBlocks'][schema_name] = custom_semafcli.cmdigraph.dataset[schema_name]
    print(custom_semafcli.cmdigraph.dataset)

semafcli.set_deposit_type('original')
semafcli.set_dataverse(ROOT, DATAVERSE_ID, API_TOKEN)
metadatafile = outputdir + output_file_name + "-output.json"
with open(metadatafile, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, ensure_ascii=False, indent=4)
if UPLOAD:
    status = semafcli.dataset_upload(metadatafile)
    print(status)

print(outputdir)
