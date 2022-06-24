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
        self.deposit = 'semantic'
        self.metadata = None

    def set_deposit_type(self, deposit):
        self.deposit = deposit
        return

    def set_dataverse(self, ROOT, DATAVERSE_ID, API_TOKEN):
        self.ROOT = ROOT
        self.DATAVERSE_ID = DATAVERSE_ID
        self.API_TOKEN = API_TOKEN
        return

    def dataset_upload(self, filename):
        if self.deposit == 'semantic':
            headers = { "X-Dataverse-key" : self.API_TOKEN, 'Content-Type' : 'application/json-ld'}
        else:
            headers = { "X-Dataverse-key" : self.API_TOKEN, 'Content-Type' : 'application/json'}

        url = "%s/%s" % (self.ROOT, "api/dataverses/%s/datasets" % self.DATAVERSE_ID)
        print(url)
        print(filename)
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
            self.metadata = self.cmdigraph.dataverse_export(self.cmdigraph.exportrecords, self.schema, defaultmetadata)
            #print(json.dumps(metadata, indent=4))
            print(json.dumps(self.cmdigraph.dataset))
            self.cmdigraph.g.serialize(format='n3', destination="/tmp/dataset.nt")
            self.semaf_filename_json = '/tmp/dataset_orig.json'
            with open(self.semaf_filename_json, 'w', encoding='utf-8') as f:
                json.dump(self.cmdigraph.dataset, f, ensure_ascii=False, indent=4)
            with open(self.semaf_filename, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=4)
            if UPLOAD:
                if self.deposit == 'semantic':
                    self.dataset = '/tmp/dataset.json'
                else:
                    self.dataset = '/tmp/dataset_orig.json'
                status = self.dataset_upload(self.dataset)
                print(status)
        return

