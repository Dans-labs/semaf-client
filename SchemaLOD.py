from rdflib import Graph, URIRef, Literal, BNode, plugin, Namespace
from rdflib.serializer import Serializer
from rdflib.plugin import register, Serializer
import numpy as np
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
        self.forbidden = ["language","authorIdentifierScheme", "contributorType", "publicationIDType", "DatasetField"]
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
        self.termURIs = {}
        self.defaultlanguage = ''
        self.serializeJSON = {}
        self.metadataframe = None
        #self.forbidden = {}
        
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
        #schema = pd.read_csv(StringIO(rawschema))
        if schemablock == 'citation':
            schema = schema[2:]
        else:
            schema = schema[2:]
        dataschema = []
    
        for i in range(0, len(schema)):
            item = schema[i]
            elements = item.split('\t')
            #print(elements)
            try:            
                if elements[keynameID] not in self.forbidden:
                    if i == len(schema):
                        dataschema.append(item)
                    else:
                        dataschema.append(item + "\n")
            except:
                skip = elements
                
        #print(dataschema)
        schemaIO = StringIO(''.join(dataschema))        
        data = pd.read_csv(schemaIO, sep="\t", error_bad_lines=False)
        print(data.columns)
        nospacefields = []
        for field in data.columns:
            newfield = field.replace(' ', '')
            nospacefields.append(newfield)
        data.columns = nospacefields

        #data = data.drop(data[data['fieldType'] == np.nan])
        if 'fieldType' in data.columns:
            data = data[data['fieldType'].notna()]
        if ' fieldType' in data.columns:
            data = data[data[' fieldType'].notna()]
            
        self.datadict[schemablock] = data

        # Mappings for termURIs
        if 'termURI' in data.columns:
            for i in data[['name','termURI']].index:
                if data.loc[i]['termURI'] is not np.nan:                    
                    self.termURIs[data.loc[i]['name']] = data.loc[i]['termURI']   
        self.metadataframe = data
                    
        return self.datadict

    def RemoveRef(self, valueURL):
        valueURL = valueURL.replace(self.RootRef, '')
        valueURL = valueURL.replace('<', '')
        valueURL = valueURL.replace('>', '')
        return valueURL
    
    def SetTermURI(self, value):
        if value in self.termURIs:
            return self.termURIs[value]
        else:
            return self.SetRef(value)
        
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
        #for row in range(0, 50):
            staID = BNode()
            nodename = self.SetRef(self.datadict[schemaname].loc[row]['name'])
            fieldtype = self.SetRef(self.datadict[schemaname].loc[row]['fieldType'])
            fieldtitle = self.datadict[schemaname].loc[row]['title']
            parentname = self.SetRef(self.datadict[schemaname].loc[row]['parent'])

            if DEBUG:
                print(nodename)
            if parentname != self.RootRef: #like 'https://dataverse.org/schema/citation/':
                staParent = self.locator[parentname]
                self.g.add((staParent, URIRef(nodename), staID))
                self.g.add((staParent, skos['broader'], URIRef(nodename)))
                self.g.add((URIRef(parentname), skos['narrower'], URIRef(nodename)))
                self.g.add((URIRef(nodename), skos['broader'], URIRef(parentname)))
                self.g.add((URIRef(nodename), skos['altLabel'], Literal(self.datadict[schemaname].loc[row]['name'])))
                self.g.add((URIRef(nodename), skos['prefLabel'], Literal(self.datadict[schemaname].loc[row]['title'])))
                if self.datadict[schemaname].loc[row]['termURI']:
                    self.g.add((URIRef(nodename), skos['exactMatch'], Literal(self.datadict[schemaname].loc[row]['termURI'])))

                self.locator[nodename] = staID      
            else:
                self.g.add((staRoot, URIRef(nodename), staID))
                self.g.add((URIRef(nodename), skos['prefLabel'], Literal(self.SetRef(self.datadict[schemaname].loc[row]['title']))))
                if self.datadict[schemaname].loc[row]['termURI']:
                    self.g.add((URIRef(nodename), skos['exactMatch'], Literal(self.datadict[schemaname].loc[row]['termURI'])))
                
                #self.g.add((staRoot, str(self.datadict[schemaname].loc[row]['name']), staID)) #vty
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
            #self.g.serialize(format='json-ld', auto_compact=True, use_rdf_type=True, destination="/tmp/%s.json-ld" % schemaname)
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

    def Info(self, fieldname=None, NESTED=None, DEBUG=None):
        triples = []
        rootname = None
        for s,p,o in schema.g.triples((URIRef(self.SetRef(fieldname)),None, None)):    
            rootname = s
            triple = [s, p, o]
            triples.append(triple)
        return triples
    
    def Relations(self, fieldname=None, NESTED=None, relation=None, DEBUG=None):
        roots = {}
        triples = []
        if 'http' in fieldname:
            searchfield = URIRef(fieldname)
        else:
            searchfield = URIRef(self.SetRef(fieldname))

        for s,p,o in self.g.triples((searchfield,None, None)):    
            if DEBUG:
                print("[DEBUG] %s %s %s\n" % (s,p,o))
            for t in [s,p,o]:
                if relation in str(Literal(t)):
                    triples.append({'s': str(s), 'p': str(p), 'o': str(o)})
        return triples
    
    def Lookup(self, fieldname=None, NESTED=None, DEBUG=None):
        lookup = {}
        for s,p,o in schema.g.triples((None, URIRef(self.SetRef(fieldname)),None)):    
            for s1,p1,o1 in schema.g.triples((o, None, None)):
            #if re.search('http', o1):
                if NESTED:
                    if not re.search('schema_|skos', p1.n3()):
                        info = {}
                        info['loc'] = o1
                        info['nested'] = 'True'
                        info['labels'] = self.Lookup(self.RemoveRef(p1.n3()))
                        info['short'] = self.RemoveRef(p1.n3())
                        lookup[p1.n3()] = info
                else:
                    info = {}
                    if DEBUG:
                        print("%s %s %s" % (s1,p1,o1))        
                    info['uri'] = o1
                    info['loc'] = p1
                    lookup[str(p1)] = info
        return lookup
    
    def Overview(self, subfield=None, condition=None, DEBUG=None):
        overview = {}
        lookup_term = None
        if subfield:
            lookup_term = URIRef(self.SetRef(subfield))
        if DEBUG:
            print(lookup_term)
        for s,p,o in self.g.triples((None, lookup_term, Literal(condition))):
            for s1,p1,o1 in self.g.triples((s, None, None)):        
                if re.search('name', p1):
                    info = {}
                    if DEBUG:
                        print("S %s %s" % (s1, o1))    
                    info['uri'] = self.SetRef(o1)
                    info['loc'] = s1
                    overview[str(o1)] = info
        return overview
    
    def get_subject(self, triple):
        return triple['s']
    def get_object(self, triple):
        return triple['o']
    def get_predicate(self, triple):
        return triple['p']

    def vocURI(self, fieldname):
        triples = self.Relations(fieldname, NESTED=True, relation='#broader')
        triplesubj = self.Relations(fieldname, NESTED=True, relation='#prefLabel')
        return ("%s#%s" % (triples[0]['o'], triplesubj[0]['o']))

    def rootURI(self,fieldname):
        triplesubj = self.Relations(fieldname, NESTED=True, relation='#prefLabel')
        if triplesubj:
            if 'http' in triplesubj[0]['o']:
                return triplesubj[0]['o']
        return fieldname

    def termURI(self, fieldname):
        triples = self.Relations(fieldname, NESTED=True, relation='#exactMatch')
        if triples:
            return self.get_object(triples[0])
        else:
            triples = self.Relations(fieldname, NESTED=True, relation='altLabel')
            if triples:
                return self.get_object(triples[0])
        if 'http' in fieldname:
            return fieldname
        return

    def default_schema(self, defaultcw):
        self.default = self.loadfile(defaultcw)
        defaultvalue = {}
        for i in self.default.index:
            fieldname = str(self.default.loc[i]['defaultfield'])
            defaultvalue[fieldname] = str(self.default.loc[i]['value'])
        return defaultvalue

    def crosswalks(self, cwURL):
        self.crosswalks_df = self.loadfile(cwURL)
        cw = {}
        for i in self.crosswalks_df.index:
            fieldname = str(self.crosswalks_df.loc[i]['originalfield'])
            cw[fieldname] = str(self.crosswalks_df.loc[i]['mappedfield'])
        return cw
    
    def Hierarchy(self, fieldname):
        #rootfield = schema.Info(fieldname, NESTED=True)  
        hierarchy = {}
        internalfields = []
        root = self.Relations(fieldname, NESTED=True, relation='#broader')        
        if root:    
            # field has top relations
            nested = self.Relations(root[0]['o'], NESTED=True, relation='#narrow') 
            hierarchy['root'] = root[0]['o']
            for n in nested:
                #nestedkey = "%sValue" % (field)
                internalfields.append(n['o'])   
            hierarchy['fields'] = internalfields
        if not internalfields:
            # fields with internal relations            
            nested = self.Relations(fieldname, NESTED=True, relation='#narrow') 
            for n in nested:
                hierarchy['root'] = n['s']
                #nestedkey = "%sValue" % (field)
                internalfields.append(n['o'])     
            hierarchy['fields'] = internalfields
        if not internalfields:
            root = self.Relations(fieldname, NESTED=True, relation='#altLabel')
        return hierarchy
