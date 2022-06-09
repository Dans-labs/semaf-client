from rdflib import Graph, URIRef, Literal, BNode, plugin, Namespace
#from rdflib.serializer import Serializer
from rdflib.plugin import register, Serializer
from collections import defaultdict, OrderedDict
import pandas as pd
import json
import requests
from io import StringIO
import re
from urllib.request import urlopen

register('json-ld', Serializer, 'rdflib_jsonld.serializer', 'JsonLDSerializer')

class Schema():
    def __init__(self, debug=False):
        self.forbidden = ["subject", "language", "authorIdentifierScheme", "contributorType", "publicationIDType", "DatasetField"]
        self.datadict = {}
        self.g = Graph()
        self.thisRef = 'https://dataverse.org/schema'
        self.RootRef = ''
        self.mappings = {}
        self.locator = {}
        self.language = 'en'
        self.CompoundNodes = []
        self.CompoundValues = {}
        self.Vertices = {}
        self.defaultlanguage = ''
        self.serializeJSON = {}
        
    def loadfile(self, filename):
        data = False
        if re.search('.csv', filename, re.IGNORECASE):
            data = pd.read_csv(filename)
        if re.search('.tsv', filename, re.IGNORECASE):            
            data = pd.read_csv(filename,sep="\t")
        elif re.search('.json', filename, re.IGNORECASE):
            response = urlopen(filename)
            json_data = response.read().decode('utf-8', 'replace')            
            data = pd.read_json(json_data) #son_normalize(json.loads(json_data))
            #OR data = pd.read_csv(filename)
        return data
        
    def emptyGraph(self):
        self.g = Graph()
        return self.g
    
    def load_metadata_schema(self, schemaURL, schemablock=False):
        keynameID = 1        
        if not schemablock:
            schemablock = 'default'
        schema = requests.get(schemaURL).text.split('\n')
        if schemablock == 'citation':
            schema = schema[2:]
        else:
            schema = schema[2:]
        dataschema = []
    
        for i in range(0, len(schema)):
            item = schema[i]
            elements = item.split('\t')
            try:
                if elements[keynameID] not in forbidden:
                    if i == len(schema):
                        dataschema.append(item)
                    else:
                        dataschema.append(item + "\n")
            except:
                skip = elements
        schemaIO = StringIO(''.join(dataschema))        
        data = pd.read_csv(schemaIO, sep="\t", error_bad_lines=False)
        self.datadict[schemablock] = data
        return self.datadict

    def SetRef(self, value):
        # Set references with loaded semantic mappings
        value = value.replace('#','')
        value = value.replace(' ','')
        if value in self.mappings:
            RefURL = self.mappings[value]
        else:
            RefURL = "%s%s" % (self.RootRef, value)
            
        return RefURL 
    
    def to_graph(self, schemaname=False, filename = False, DEBUG=False):
        self.RootRef = "%s/%s/" % (self.thisRef, schemaname)
        
        if schemaname not in self.datadict:
            return

        self.g = self.emptyGraph()
        ns1 = Namespace(self.RootRef)
        self.g.bind(schemaname, ns1)
        skos = Namespace('http://www.w3.org/2004/02/skos/core#')
        self.g.bind('skos', skos)
        
        self.datadict[schemaname].fillna('', inplace=True)
        tmpnames = self.datadict[schemaname].columns
        names = []
        for name in tmpnames:
            newname = "schema_%s" % name
            names.append(newname)
        staRoot = URIRef(self.RootRef)
        
        for row in range(0, self.datadict[schemaname]['name'].size):              
            staID = BNode()
            nodename = self.SetRef(self.datadict[schemaname].loc[row]['name'])
            parentname = self.SetRef(self.datadict[schemaname].loc[row]['parent'])

            if DEBUG:
                print(nodename)
            if parentname != self.RootRef: #like 'https://dataverse.org/schema/citation/':
                staParent = self.locator[parentname]
                self.g.add((staParent, URIRef(nodename), staID))
                self.g.add((staParent, skos['broader'], URIRef(nodename)))
                self.locator[nodename] = staID      
            else:
                self.g.add((staRoot, URIRef(nodename), staID))
                #self.g.add((URIRef(nodename), skos['narrower'], URIRef(parentname)))
                self.locator[nodename] = staID
            
            statement = staID
            for i in range(0, self.datadict[schemaname].loc[row].size-1):                                
                item = self.datadict[schemaname].loc[row].values[i]
                if item:
                    if self.defaultlanguage:
                        self.g.add((statement, URIRef(self.SetRef(names[i])), Literal(item, lang=self.defaultlanguage)))
                    else:
                        self.g.add((statement, URIRef(self.SetRef(names[i])), Literal(item)))
                #self.g.add((statement, URIRef(self.SetRef(names[i])), Literal("%s NL" % item, lang='nl')))
        
        # Save to files
        if filename:
            self.g.serialize(format='n3', destination="/tmp/%s.nt" % schemaname)
            self.g.serialize(format='json-ld', auto_compact=True, use_rdf_type=True, destination="/tmp/%s.json-ld" % schemaname)
        return self.g            

    def isNode(self, pNode): 
        if pNode:
            checkNode = str(pNode)[:3]                
            if checkNode == '_:N':  
                return pNode
            else:
                return False
        return False
                        
    def CompoundElements(self, jsongraph, DEBUG=None):
        for compoundkey in jsongraph:
            #isEdge = False
            rootNodeID = None
            for key in compoundkey:  
                if key == '@id':
                    if DEBUG:
                        print("KEY %s / %s" % (self.isNode(compoundkey[key]), compoundkey[key]))
                    rootNodeID = compoundkey[key]
                for i in range(0, len(compoundkey[key])):
                    if '@id' in compoundkey[key][i]:
                        nodeID = compoundkey[key][i]['@id']
                        if self.isNode(nodeID):                            
                            self.CompoundNodes.append(nodeID) 
                            self.CompoundValues[nodeID] = compoundkey[key][i]
                            cv = nodeID
                            if DEBUG:
                                print("\t%s\n" % compoundkey[key][i]['@id']) 
            if self.isNode(rootNodeID):
                self.CompoundValues[rootNodeID] = compoundkey
            else:
                self.Vertices[rootNodeID] = compoundkey
                #print("%s => %s\n" % (self.isNode(rootNodeID), compoundkey))

        randomNode = None
        for rootNodeID in self.Vertices:
            #print("%s => %s\n" % (self.isNode(rootNodeID), compoundkey))
            compoundkey = self.Vertices[rootNodeID]            
            for key in compoundkey:         
                newfields = {}
                if '@id' in compoundkey[key][0]:
                    nodeID = compoundkey[key][0]['@id']
                    if DEBUG:
                        print("%s %s" % (key, nodeID))
                    extra = []
                    if nodeID in self.CompoundValues:
                        #self.serializeJSON[key] = self.CompoundValues[nodeID]
                        extra.append(self.CompoundValues[nodeID])
                        randomNode = nodeID
                        #extra['nodeID'] = nodeID
                        x = False
                    self.serializeJSON[key] = extra
                else:                    
                    self.serializeJSON[key] = compoundkey[key]
        #print(self.CompoundValues[cv])
        return randomNode
        return self.serializeJSON

    def Lookup(self, fieldname=None):
        for s,p,o in schema.g.triples((None, URIRef(self.SetRef(fieldname)),None)):    
            for s1,p1,o1 in schema.g.triples((o, None, None)):
            #if re.search('http', o1):
                print("%s %s %s" % (s1,p1,o1))        
        return
