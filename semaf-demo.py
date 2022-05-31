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

sm = Semaf()
schema = Schema()
cmdifile = '0b01e4108004e49d_INV_REG_REPARATIE_CONSUMENTENARTIKELEN_HANDEL_2008-01-01.dsc'

if cmdifile:
    # Read file and load in the knowledge graph
    s = sm.loadcmdi(cmdifile)
    defaultvalue = schema.default_schema(cbs_default_crosswalks)
    schemapd = schema.load_metadata_schema(schemaURL, 'citation')

    # Load schema
    schema.to_graph('citation', filename='citation')
    crosswalks = schema.crosswalks(crosswalks_location)

    cmdigraph = GraphBuilder(sm.json, "https://dataverse.org/schema/cbs/", graphformat='rich')
    defaultmetadata = cmdigraph.get_default_metadata(schema, defaultvalue) 
    mappedjson = cmdigraph.set_cvserver(cv_server)
    cmdigraph.set_crosswalks(crosswalks)
    items = cmdigraph.rotate(cmdigraph.context, False)
    mappedjson = cmdigraph.iterator(json.loads(sm.json))

    if schema:
        metadata = cmdigraph.dataverse_export(cmdigraph.exportrecords, schema, defaultmetadata)
        print(json.dumps(metadata, indent=4))
