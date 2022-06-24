from xml.dom import minidom
#from CLARIAH_CMDI.xml2dict.processor import CMDI # load, xmldom2dict
import json
from SchemaLOD import Schema, GraphBuilder
from SemafCLI import SemafUtils
from config import default_crosswalks_location, crosswalks_location, cbs_default_crosswalks
from rdflib import Graph, URIRef, Literal, BNode, plugin, Namespace
from rdflib.serializer import Serializer
from rdflib.namespace import RDF, RDFS
from config import cmdifile, ROOT, DATAVERSE_ID, API_TOKEN, schemaURL, cv_server, cwfile
from Semaf import Semaf
from jGraph import jGraph
import sys
import requests
from datetime import datetime

UPLOAD = False
if len(sys.argv) > 1:
    cmdifile = sys.argv[1]
    if len(sys.argv) > 2:
        UPLOAD = True
else:
    print("XML file required as input parameter")
    exit()
    #cmdifile = '0b01e4108004e49d_INV_REG_REPARATIE_CONSUMENTENARTIKELEN_HANDEL_2008-01-01.dsc'

semafcli = SemafUtils(cbs_default_crosswalks, crosswalks_location)
semafcli.set_deposit_type('original')
semafcli.set_dataverse(ROOT, DATAVERSE_ID, API_TOKEN)
semafcli.transformation(cmdifile, UPLOAD)
print(semafcli.dataset)
