from xml.dom import minidom
#from CLARIAH_CMDI.xml2dict.processor import CMDI # load, xmldom2dict
import json
from SchemaLOD import Schema, GraphBuilder
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

class SemafUtils():
    def __init__(self, default_crosswalks, crosswalks_location, debug=False):
        self.default_crosswalks = default_crosswalks
        self.crosswalks_location = crosswalks_location
        self.semaf_filename = '/tmp/dataset.json'
        self.cv_server = ''

    def set_dataverse(self, ROOT, DATAVERSE_ID, API_TOKEN):
        self.ROOT = ROOT
        self.DATAVERSE_ID = DATAVERSE_ID
        self.API_TOKEN = API_TOKEN
        return

    def dataset_upload(self, filename):
        headers = { "X-Dataverse-key" : API_TOKEN, 'Content-Type' : 'application/json-ld'}
        url = "%s/%s" % (ROOT, "api/dataverses/%s/datasets" % DATAVERSE_ID)
        r = requests.post(url, data=open(filename, 'rb'), headers=headers)
        return r.text

    def transformation(self, cmdifile, UPLOAD=False): 
        self.sm = Semaf()
        self.schema = Schema()
       
        # Read file and load in the knowledge graph
        s = self.sm.loadcmdi(cmdifile)
        defaultvalue = self.schema.default_schema(self.default_crosswalks)
        schemapd = self.schema.load_metadata_schema(schemaURL, 'citation')

        # Load schema
        self.schema.to_graph('citation', filename='citation')
        crosswalks = self.schema.crosswalks(self.crosswalks_location)

        self.cmdigraph = GraphBuilder(self.sm.json, "https://dataverse.org/schema/cbs/", graphformat='rich')
        defaultmetadata = self.cmdigraph.get_default_metadata(self.schema, defaultvalue) 
        mappedjson = self.cmdigraph.set_cvserver(self.cv_server)
        self.cmdigraph.set_crosswalks(crosswalks)
        items = self.cmdigraph.rotate(self.cmdigraph.context, False)
        mappedjson = self.cmdigraph.iterator(json.loads(self.sm.json))

        if self.schema:
            metadata = self.cmdigraph.dataverse_export(self.cmdigraph.exportrecords, self.schema, defaultmetadata)
            print(json.dumps(metadata, indent=4))
            self.cmdigraph.g.serialize(format='n3', destination="/tmp/dataset.nt")
            with open(self.semaf_filename, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=4)
            if UPLOAD:
                status = self.dataset_upload(ROOT, DATAVERSE_ID, API_TOKEN, semaf_filename)
                print(status)
        return

