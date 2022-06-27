from rdflib import Graph, URIRef, Literal, BNode, plugin, Namespace
from rdflib.serializer import Serializer
from rdflib.plugin import register, Serializer
import numpy as np
from collections import defaultdict, OrderedDict
import pandas as pd
import json
import requests
from io import StringIO
from rdflib.namespace import RDF, RDFS
import re
from urllib.request import urlopen

register('json-ld', Serializer, 'rdflib_jsonld.serializer', 'JsonLDSerializer')

class Schema():
    def __init__(self, graph=None, debug=False):
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
        self.cv_server = ''
        self.alias = {}
        self.parents = {}
        self.order = {}
        self.allowmulti = {}

        if graph:
            self.g = graph
        
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

    def get_alias(self, field):
        if field in self.alias:
            return self.alias[field]
        return field

    def get_fields_order(self):
        order = []
        for x in dict(sorted(self.order.items(), key=lambda item: item[1])):
            order.append(x)
        return order
    
    def load_metadata_schema(self, schemaURL, schemablock=False):
        keynameID = 1        
        if not schemablock:
            schemablock = 'default'
        self.RootRef = "%s/%s/" % (self.thisRef, schemablock) 
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
        if not 'termURI' in data.columns:
            data.insert(1, 'termURI', '', True)

        if schemablock:
            for i in data[['name','termURI']].index:
                if data.loc[i]['termURI'] is not np.nan:                    
                    self.termURIs[data.loc[i]['name']] = data.loc[i]['termURI']   
        # Building alias mapping
        for i in data[['name','title','parent','displayOrder','allowmultiples']].index:
            self.alias[data.loc[i]['name']] = data.loc[i]['title']
            self.order[data.loc[i]['name']] = int(data.loc[i]['displayOrder'])
            if data.loc[i]['allowmultiples']:
                self.allowmulti[data.loc[i]['name']] = True
            else:
                self.allowmulti[data.loc[i]['name']] = False
            self.alias[self.SetTermURI(data.loc[i]['name'])] = data.loc[i]['title']
            self.alias[self.SetRef(data.loc[i]['name'])] = data.loc[i]['title']
            if data.loc[i]['parent']:
                self.parents[data.loc[i]['name']] = data.loc[i]['parent']
        self.metadataframe = data
        self.alias['test'] = 'test'
                    
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
        #value = value.replace(' ','')
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
    def clearpath(self, xpath):
        return xpath.replace('#document', '')

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
        else:
            if fieldname in self.alias:
                return "%s" % self.SetRef(self.alias[fieldname])
            else:
                return "%s" % self.SetRef(fieldname)
        return

    def default_schema(self, defaultcw):
        self.default = self.loadfile(defaultcw)
        defaultvalue = {}
        if 'defaultfield' in self.default.columns:
            for i in self.default.index:
                fieldname = str(self.default.loc[i]['defaultfield'])
                defaultvalue[fieldname] = str(self.default.loc[i]['value'])
        if 'metadatablock' in self.default.columns:
            for i in self.default.index:
                fieldname = str(self.default.loc[i]['subfield'])
                defaultvalue[fieldname] = str(self.default.loc[i]['value'])

        return defaultvalue

    def crosswalks(self, cwURL):
        self.crosswalks_df = self.loadfile(cwURL)
        cw = {}
        if 'mappedfield' in self.crosswalks_df.columns:
            for i in self.crosswalks_df.index:
                fieldname = str(self.crosswalks_df.loc[i]['originalfield'])
                cw[fieldname] = str(self.crosswalks_df.loc[i]['mappedfield'])
        if 'metadatablock' in self.crosswalks_df.columns: 
            for i in self.crosswalks_df.index:
                fieldname = str(self.crosswalks_df.loc[i]['originalfield'])
                cw[fieldname] = str(self.crosswalks_df.loc[i]['subfield'])
        return cw
    
    def Hierarchy(self, fieldname):
        #rootfield = schema.Info(fieldname, NESTED=True)  
        hierarchy = {}
        hierarchy['original'] = fieldname
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

class GraphBuilder():
    def __init__(self, thisobject=None, RootRef=None, crosswolksfile=None, thisformat='json', graphformat=None, debug=False):
        self.stats = {}
        self.json = {}
        self.context = json.loads(thisobject)
        self.RootRef = RootRef
        self.exportdata = {}
        self.exportrecords = []
        self.dictcontent = []
        self.mappings = {}
        self.locator = {}
        self.namespaces = {}
        self.EnrichFlag = False
        self.crosswalks = {}
        self.cv_server = ''
        # Default Graph 
        self.g = Graph()
        self.level = 0
        self.format = None
        self.crosswalks = None
        self.statements = []
        self.dataset = {}
        self.datasetfields = []
        self.compound = {}

        if self.format:
            self.format = graphformat

    def mapping(self, fieldname):
        if fieldname in self.crosswalks.keys():
            return fieldname #self.crosswalks[fieldname]
        return #fieldname

    def iterator(self, x, xpath=''):      
        xpath = self.clearpath(xpath)  
        if isinstance(x, list):            
            thisblock = []            
            #if self.mapping(x):
            #return [self.iterator(v, previous_key) for v in x]
            for i in range(0, len(x)):
                v = x[i]
                if xpath:
                    #thispath = "%s/%s" % (xpath, v)
                    thispath = xpath
                else:
                    thispath = "/%s" % v
                #m = self.mapping(thispath)
                #if m:
                #    self.exportdata[m] = v
                thisblock.append({'xpath': thispath, 'block': "%s/%s" % (thispath, str(i)), 'value': self.iterator(v, thispath)})                
            return thisblock
        elif isinstance(x, dict):              
            thisblock = {}
            #return { self.mapping(k): self.iterator(v, xpath) for k,v in x.items() }
            for k,v in x.items():
                if xpath:
                    thispath = "%s/%s" % (xpath, k)
                else:
                    thispath = "/%s" % k         
                #m = self.mapping(thispath)
                #if m:
                #    self.exportdata[m] = v
                thisblock[k] = { 'xpath': thispath, 'value': self.iterator(v, thispath) }
            return thisblock
        else:
            m = self.mapping(xpath)
            if m:
                self.exportdata[m] = x            
                self.exportrecords.append({'xpath': xpath, 'mapping': self.crosswalks[xpath],'value': x})
            return self.clearpath(x)

    def set_cvserver(self, cv_server):
        self.cv_server = cv_server
        return

    def externalCV(self, concept):
        url = "%s/%s" % (self.cv_server, "/rest/v1/search?vocab=cbs&query=%s" % concept)
        response = requests.get(url)
        staID = BNode()
        EXISTS = False
        self.g.add((staID, self.skosxl['literalForm'], Literal(concept)))
        if response.status_code == 200:
            CVdata = json.loads(response.content.decode('utf-8'))['results']
            for cvobject in CVdata:
                self.g.add((staID, self.skos['note'], Literal('Skosmos concept')))
                for k, v in cvobject.items():
                    EXISTS = True
                    if k == 'prefLabel':
                        self.g.add((staID, self.skos['prefLabel'], Literal(v)))
                    if k == 'altLabel':
                        self.g.add((staID, self.skos['altLabel'], Literal(v)))
            if EXISTS:
                return staID
            else:
                return
        return

    def clearpath(self, xpath=''):
        if xpath:
            xpath = xpath.replace('#document', '')
            xpath = xpath.replace('//', '/')
            return xpath
        return

    def set_crosswalks(self, cw):
        self.crosswalks = cw
           
    def SetRef(self, value):
        # Set references with loaded semantic mappings
        #if value:
        #    value = self.clearpath(value)
        #    if value:
        #        if str(value)[0] == '/':
        #            value = value.lstrip()

        if value in self.mappings:
            RefURL = self.mappings[value]
        else:
            RefURL = "%s%s" % (self.RootRef, value)
        self.crosswalks[RefURL] = value
        #self.mappings[value] = RefURL
        return RefURL
    
    def setNamespaces(self):
        # Define namespaces
        ns1 = Namespace("%s" % self.RootRef)
        self.g.bind('cmdi', ns1)
        ns2 = Namespace("%s/#" % self.RootRef)
        self.g.bind('cmdidoc', ns2)
        ns3 = Namespace("%s/Keyword#" % self.RootRef)
        self.g.bind('keywords', ns3)
        ns4 = Namespace("https://dataverse.org/schema/citation")
        self.g.bind('citation', ns4)
        ns5 = Namespace("https://dataverse.org/schema/")
        self.g.bind('schema', ns5)
        ns6 = Namespace("http://purl.org/dc/terms/")
        self.g.bind('dcterms', ns6)

        for nsname in self.namespaces:
            ns = Namespace(nsname)
            self.g.bind(self.namespaces[nsname], "%s/" % ns)    
        return

    def load_crosswalks(self, crossfile):
        with open(crossfile, encoding='utf-8') as fh:
            content = fh.readlines()
            for line in content:
                mapline = line.split(',')
                self.mappings[mapline[0]] = mapline[1]
        return self.mappings
    
    def rotatelist(self, thislist, previous_element, xpathroot, DEBUG=None):
        # previous_element = parent key
        # k = key
        # v = value
        #self.level = self.level + 1
        self.level = 0 
        # some default variables
        root = ''
        k = ''

        for keyID in range(0, len(thislist)):
            key = thislist[keyID]
            if type(key) is dict:
                complexstatements = {}
                staID = BNode()
                staIDlocal = BNode()
                for k, v in key.items():
                    #root="%s/%s" % (self.RootRef, previous_element)
                    root = self.SetRef(previous_element)
                    # vty xpathroot = "%s/%s" % (xpathroot, k)
                    #kRef = "%s/%s" % (self.RootRef, k)
                    self.dictcontent.append({"list": root, "xpath": xpathroot, self.SetRef(k): v, 'type': type(v), 'sort': keyID })
                    if type(v) is str:
                        complexstatements[URIRef(self.SetRef(k))] = v
                        staIDstr = BNode()
                        #self.g.add((staIDstr, URIRef(self.SetRef(k)), Literal(item)))                        
                        self.g.add((staIDstr, URIRef(self.SetRef(k)), Literal(v)))
                        self.g.add((staIDstr, URIRef(self.SetRef(k)), Literal(v)))
                        self.g.add((staIDstr, self.skosxl['hiddenLabel'], Literal(self.clearpath("%s/%s" % (xpathroot, k)))))
                        self.g.add((staIDstr, RDF.value, Literal(v)))
                        self.statements.append({'xpath': self.clearpath("%s/%s" % (xpathroot, k)), 'value': v })
                        
                        if self.format == 'rich':
                            self.g.add((staIDstr, self.skosxl['note'], Literal('internal statement')))
                            self.g.add((staIDstr, self.skosxl['literalForm'], Literal(k)))
                        
                        #conceptgraph = self.externalCV(self.cv_server, v)
                        conceptgraph = None
                        if conceptgraph:
                            self.g.add((staIDstr, self.skos['exactMatch'], conceptgraph))
                        self.g.add((staIDlocal, URIRef(self.SetRef(k)), staIDstr))                            

                    elif type(v) is list:
                        complexarray = []
                        for item in v:
                            self.level = self.level + 1
                            complexarray.append({ self.SetRef(k): item, URIRef("%s#Vocabulary" % self.SetRef(k)) : "url" })
                            
                            # Create and add a new statement in the graph
                            staIDar = BNode()
                            self.g.add((staIDar, URIRef(self.SetRef(k)), Literal(item)))
                            self.g.add((staIDar, self.skosxl['hiddenLabel'], Literal(self.clearpath("%s/%s" % (xpathroot, k)))))
                            # vty self.g.add((staIDar, self.skos['broader'], Literal(previous_element)))
                            self.g.add((staIDar, self.skos['broader'], URIRef(self.SetRef(previous_element))))
                            self.g.add((staIDar, self.skos['prefLabel'], Literal(k)))
                            self.g.add((staIDar, RDF.value, Literal(item)))
                            if self.format == 'rich':
                                self.g.add((staIDar, self.skos['note'], Literal(self.level)))
                                self.g.add((staIDar, self.skosxl['literalForm'], Literal(k)))
                                self.g.add((staIDar, self.skosxl['note'], Literal('cycle statement')))
                            
                            if self.EnrichFlag:
                                self.g.add((staIDar, URIRef("%s#Vocabulary" % self.SetRef(k)), Literal('vocabulary name')))
                                self.g.add((staIDar, URIRef("%s#VocabularyURL" % self.SetRef(k)), Literal("http link to concept URI for %s" % item)))
                            # Add statements from array
                            self.g.add((staIDlocal, URIRef(self.SetRef(k)), staIDar))
                        complexstatements[URIRef(self.SetRef(k))] = complexarray
                    if DEBUG:
                        print(complexstatements)
                self.g.add((URIRef(root), URIRef(self.SetRef(k)), staIDlocal))
        return
    
    def rotate(self, thisdict, previous_element, DEBUG=None):
        self.cmdiloc = {}

        skos = Namespace('http://www.w3.org/2004/02/skos/core#')
        self.g.bind('skos', skos)        
        skosxl = Namespace('http://www.w3.org/2008/05/skos-xl#')
        self.skos = Namespace('http://www.w3.org/2004/02/skos/core#')
        self.skosxl = Namespace('http://www.w3.org/2008/05/skos-xl#')
        self.g.bind('skosxl', skosxl)        
        
        if (isinstance(thisdict,list)):
            #root="%s/%s" % (self.RootRef, previous_element)
            root = self.SetRef(previous_element)
            #kRef = "%s/%s" % (self.RootRef, k)
            self.dictcontent.append({"list": root, self.SetRef(k): v })
            #print("%s" % root)
            self.g.add((URIRef(root), URIRef(self.SetRef(k)), Literal(v)))
            self.g.add((URIRef(root), skos['prefLabel'], Literal(root)))
            #self.g.add(((URIRef(root), skos['altLabel'], Literal(k)))            
            return

        for k,v in thisdict.items():
            if (isinstance(v,dict)):
                if previous_element:
                    fullXpath = "%s/%s" % (previous_element, k)
                else:
                    fullXpath = k
                self.namespaces[self.SetRef(previous_element)] = k.lower()
                # vty if DEBUG:
                #print("XPath %s [%s/%s]" % (fullXpath, previous_element, k))
                self.rotate(v, fullXpath)
                ###self.rotate(v, k)
                #root="%s%s" % (self.RootRef, previous_element)
                root = self.SetRef(previous_element)
                #kRef = "%s/%s" % (self.RootRef, k)
                staID = BNode()
                staID = URIRef(self.RootRef)
                self.g.add((staID, URIRef(root), URIRef(self.SetRef(k))))
                #self.g.add((staID, skos['broader'], URIRef(nodename)))
                self.g.add((staID, skos['hiddenLabel'], Literal(self.clearpath(fullXpath))))
                self.g.add((staID, skos['altLabel'], Literal(k)))
                self.g.add((staID, RDF.value, Literal(v)))
                if self.format == 'rich':
                    self.g.add((staID, skos['note'], Literal('simple statement')))
                self.locator[root] = staID
                continue
            else:
                if (isinstance(v,list)):
                    if DEBUG:
                        print(k)
                    xpathroot = "%s/%s" % (previous_element, k)
                    self.rotatelist(v, k, xpathroot)
                    continue
                #root="%s%s" % (self.RootRef, previous_element)
                root = self.SetRef(previous_element)
                xpathroot = "%s/%s" % (previous_element, k)
                if DEBUG:
                    print(self.cmdiloc)
                #kRef = "%s/%s" % (self.RootRef, k)

                if self.SetRef(k) in self.cmdiloc:
                    try:
                        cache = self.cmdiloc['root']
                    except: 
                        cache = []

                    if type(cache) is list:
                        cache.append( { self.SetRef(k): v })
                    else:
                        cache = { self.SetRef(k): v }
                else:
                    self.cmdiloc = { self.SetRef(k): v }
                self.dictcontent.append({"parent": root, "xpath": xpathroot, self.SetRef(k): v, 'type': type(v) })

                # Link root and parents
                self.g.add((URIRef(root), skos['narrower'], URIRef(self.SetRef(k))))  

                # Add statement
                staID = BNode()
                self.locator[URIRef(self.SetRef(k))] = staID
                ### outdated self.g.add((URIRef(root), URIRef(self.SetRef(k)), Literal(v)))  
                #self.g.add((staID, skos['note1'], Literal(k)))
                self.g.add((URIRef(root), skosxl['hiddenLabel'], Literal(self.clearpath(xpathroot))))                
                self.g.add((URIRef(root), skos['broader'], URIRef(root)))
                if self.format == 'rich':
                    self.g.add((URIRef(root), skosxl['literalForm'], Literal(k)))
                    self.g.add((URIRef(root), skos['note'], Literal('parent statement')))
                                
                #self.g.add((URIRef(root), skosxl['Label'], Literal(k)))
                self.g.add((staID, skos['literalForm'], Literal(k)))
                self.g.add((staID, skosxl['hiddenLabel'], Literal(self.clearpath("%s" % (previous_element)))))
                self.g.add((staID, URIRef(self.SetRef(k)), Literal(v)))
                self.g.add((staID, RDF.value, Literal(v)))
                if self.format == 'rich':
                    self.g.add((staID, skos['note'], Literal('compound statement')))
                self.g.add((staID, skos['broader'], URIRef(root)))
                
                #self.g.add((URIRef(root), skosxl['LabelRelation'], staID))
                self.g.add((URIRef(self.SetRef(k)), skosxl['LabelRelation'], staID))
                self.g.add((URIRef(self.SetRef(k)), skosxl['hiddenLabel'], Literal(self.clearpath(xpathroot))))  ### ???
                self.g.add((URIRef(self.SetRef(k)), skos['broader'], URIRef(root)))            
                if self.format == 'rich':
                    self.g.add((URIRef(self.SetRef(k)), skosxl['literalForm'], Literal(k)))  
                    self.g.add((URIRef(self.SetRef(k)), skos['note'], Literal('compound statements container')))                  

        self.setNamespaces()
        return self.dictcontent

    def get_default_metadata(self, schema, defaultvalue):
        self.defaultmetadata = {}
        for i in schema.default.index:
            fieldname = str(schema.default.loc[i]['subfield'])
            #print(fieldname)
            cfields = schema.Hierarchy(fieldname)
            #print(cfields)
            if not cfields['fields']:
                # field without children
                triples = schema.Relations(fieldname, NESTED=True, relation='#exactMatch')
                if triples:
                    self.defaultmetadata[schema.get_object(triples[0])] = schema.default.loc[i]['value']
                    thistype = {}
                    thistype['typeName'] = fieldname # schema.get_object(triples[0])
                    if fieldname == 'subject':
                        thistype['typeClass'] = 'controlledVocabulary'
                        thistype['multiple'] = True
                        thistype['value'] = [ schema.default.loc[i]['value'] ]
                    else:
                        thistype['typeClass'] = 'primitive'
                        thistype['multiple'] = False
                        thistype['value'] = schema.default.loc[i]['value']

                    #thistype['default'] = 'default'
                    self.datasetfields.append(thistype)

            else:
                metadatablock = {}
                compoundvalues = []
                values = {}
                for extrafield in cfields['fields']:
                    triples = schema.Relations(extrafield, NESTED=True, relation='#altLabel')
                    #print("\t %s => %s " % (extrafield, schema.get_object(triples[0])))
                    if schema.get_object(triples[0]) in defaultvalue:
                        vocnameS = schema.get_subject(triples[0])
                        vocname = schema.vocURI(vocnameS)
                        metadatablock[vocname] = defaultvalue[schema.get_object(triples[0])]
                        valuedict = { 'typeName': schema.RemoveRef(vocnameS), 'multiple': schema.allowmulti[schema.RemoveRef(vocnameS)], 'typeClass': 'primitive', 'value': defaultvalue[schema.get_object(triples[0])] }
                        #valuekey = { schema.RemoveRef(vocnameS) : valuedict }
                        values[schema.RemoveRef(vocnameS)] = valuedict
                        #compoundvalues.append(valuekey)

                    #thistype['value'] = compoundvalues #{ str(schema.parents[thisfield]): compoundvalues }

                # Keep compound values in arrary
                if fieldname in schema.parents:
                    rootfield = schema.parents[fieldname]
                else:
                    rootfield = fieldname

                self.compound[rootfield] = [ values ] #compoundvalues
#                if rootfield in self.compound:
#                    self.compound[rootfield].append(values) #compoundvalues[0])
#                else:
#                    self.compound[rootfield] = [ values ] # compoundvalues

                self.defaultmetadata[schema.rootURI(schema.termURI(cfields['root']))] = metadatablock
        return self.defaultmetadata

    def dataverse_export_lod(self, data, schema, savedmetadata=None):        
        metadata = {}
        if savedmetadata:
            metadata = savedmetadata
        DEBUG = False 
        for thisitem in data: #.items():
            field = thisitem['xpath']
            thisvalue = thisitem['value']
            if field in self.crosswalks:       
                thisfield = self.crosswalks[field] 
                nested = schema.Hierarchy(thisfield)
                if DEBUG:
                    print("[DEBUG] Field %s" % thisfield)
                    print("[DEBUG] Nested: %s" % str(nested))

                # If element has children
                if 'root' in nested:
                    metadatablock = {}
                    valuefield = "%sValue" % thisfield
                    for field in nested['fields']:                
                        #if field in newfields:
                        if DEBUG:
                            print("\t\t %s %s" % (field, schema.vocURI(field)))
                        if schema.termURI(field) == schema.termURI(thisfield) or 'Value' in field: 
                            #schema.termURI(field) == schema.termURI(valuefield):
                            metadatablock[schema.vocURI(field)] = thisvalue
                    if DEBUG:
                        print("Block %s" % str(metadatablock))
                    root = schema.rootURI(nested['root'])
                    if root in metadata:
                        if type(metadata[root]) == dict:
                            current = metadata[root]
                            block = []
                            block.append(current)
                            if current != metadatablock:
                                block.append(metadatablock)
                            metadata[root] = block
                        else:
                            metadata[root].append(metadatablock)
                    else:
                        metadata[schema.rootURI(nested['root'])] = metadatablock
                else:
                    termURI = schema.termURI(thisfield)
                    if termURI:
                        if DEBUG:
                            print("\t Term %s" % termURI)
                        metadata[termURI] = thisvalue
        return metadata        

    def dataverse_export(self, data, schema, schema_name, savedmetadata=None):
        metadata = {}
        if savedmetadata:
            metadata = savedmetadata
        DEBUG = False
        for thisitem in data: #.items():
            field = thisitem['xpath']
            thisvalue = thisitem['value']
            if field in self.crosswalks:
                thisfield = self.crosswalks[field]
                nested = schema.Hierarchy(thisfield)
                DEBUGX = False
                thistype = {}
                thistype['typeName'] = thisfield
                    
                #thistype['nested'] = nested
                if DEBUGX:                    
                    print("[DEBUG] Field %s" % thisfield)
                    print("[DEBUG] Nested: %s" % str(nested))

                # If element has children
                if 'root' in nested:
                    if thisfield in schema.parents:
                        thistype['typeName'] = schema.parents[thisfield]
                    else:
                        thistype['typeName'] = thisfield
                    
                    thistype['typeClass'] = 'compound'
                    thistype['multiple'] = schema.allowmulti[thistype['typeName']]                    
                    metadatablock = {}
                    valuefield = "%sValue" % thisfield
                    
                    compoundvalues = []
                    for field in nested['fields']:                        
                        if DEBUG:
                            print("\t\t %s %s" % (field, schema.vocURI(field)))
                        if schema.termURI(field) == schema.termURI(thisfield) or 'Value' in field:
                            #schema.termURI(field) == schema.termURI(valuefield):
                            metadatablock[schema.vocURI(field)] = thisvalue
                            valuedict = { 'typeName': schema.RemoveRef(field), 'multiple': schema.allowmulti[schema.RemoveRef(field)], 'typeClass': 'primitive', 'value': thisvalue }
                            valuekey = { schema.RemoveRef(field) : valuedict }
                            compoundvalues.append(valuekey)
                    
                    thistype['value'] = compoundvalues #{ str(schema.parents[thisfield]): compoundvalues }
                    # Keep compound values in arrary
                    rootfield = thistype['typeName']
                    #self.compound[rootfield] = compoundvalues

                    if rootfield in self.compound:
                        self.compound[rootfield].append(compoundvalues[0])
                    else:
                        self.compound[rootfield] = compoundvalues

                    if DEBUG:
                        print("Block %s" % str(metadatablock))
                        
                    root = schema.rootURI(nested['root'])
                    if root in metadata:
                        if type(metadata[root]) == dict:
                            current = metadata[root]
                            block = []
                            block.append(current)
                            if current != metadatablock:
                                block.append(metadatablock)
                            metadata[root] = block
                        else:
                            metadata[root].append(metadatablock)
                    else:
                        metadata[schema.rootURI(nested['root'])] = metadatablock

                else:
                    print(thisfield)
                    thistype['typeClass'] = 'primitive'
                    try:
                        thistype['multiple'] = schema.allowmulti[schema.RemoveRef(thisfield)]
                    except:
                        thistype['multiple'] = False

                    repeated = False
                    if 'kindOfData' in thisfield:
                        repeated = True
                    if 'variable' in thisfield:
                        repeated = True

                    if repeated:
                        thistype['value'] = [ thisvalue ]
                    else:
                        thistype['value'] = thisvalue # { thisfield: thisvalue }

                    termURI = schema.termURI(thisfield)
                    if termURI:
                        if DEBUG:
                            print("\t Term %s" % termURI)
                        metadata[termURI] = thisvalue
                
                if not thistype['typeName'] in self.compound:
                    self.datasetfields.append(thistype)
                #self.dataset[] = thistype

        # Finalizing dataset
        self.vocab = {}
        for keyword in self.compound:
            x = { "%s tmp" % keyword: self.compound[keyword]  }
            compitem = { 'typeName': keyword, 'multiple': schema.allowmulti[keyword], 'typeClass': 'compound', 'value': self.compound[keyword] }
            self.datasetfields.append(compitem) # { 'value': [ x ] } )
            self.vocab = { str(compitem) : keyword }
                
        self.thisorder = {}
        for item in self.datasetfields:
            name = item['typeName']
            if name in schema.order:
                self.thisorder[name] = item

        fields = []
        for field in schema.get_fields_order():
            #if field in self.thisorder:
            for item in self.datasetfields:
                allfields = ['title', 'author', 'datasetContact', 'dsDescription', 'subject', 'keyword']
                if field == item['typeName']: # in allfields:
                    fields.append(item) #self.thisorder[field])

        self.dataset = {}
        self.fields = { 'fields': fields }
        self.citation = { schema_name: self.fields }
        if schema_name == 'citation':
            self.metadatablocks = { 'metadataBlocks': self.citation }
            self.dataset = {'datasetVersion': self.metadatablocks } 
        else:
            self.dataset = self.citation
        return metadata

