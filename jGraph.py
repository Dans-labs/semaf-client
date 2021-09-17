from xml.dom import minidom
import json
from Semaf import Semaf
from rdflib import Graph, URIRef, Literal, BNode, plugin, Namespace
from rdflib.serializer import Serializer
from collections import defaultdict, OrderedDict
import requests

class jGraph():
    def __init__(self, thisobject=None, RootRef=None, crosswolksfile=None, thisformat='json', debug=False):
        self.stats = {}
        self.json = {}
        self.context = json.loads(thisobject)
        self.RootRef = RootRef 
        self.dictcontent = []
        self.mappings = {}
        self.locator = {}
        self.namespaces = {}
        self.EnrichFlag = False
        #self.EnrichFlag = True
        self.crosswalks = {}
        # Default Graph 
        self.g = Graph()
        
        # Second graph reservation 
        #self.gs = Graph()

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

    def SetRef(self, value):
        # Set references with loaded semantic mappings
        if value in self.mappings:
            RefURL = self.mappings[value]
        else:
            RefURL = "%s%s" % (self.RootRef, value)
        self.crosswalks[RefURL] = value
        #self.mappings[value] = RefURL
        return RefURL        
        
    def load_crosswalks(self, crossfile):        
        with open(crossfile, encoding='utf-8') as fh:
            content = fh.readlines()
            for line in content:                
                mapline = line.split(',')                
                self.mappings[mapline[0]] = mapline[1]
        return self.mappings
            
    def rotatelist(self, thislist, pk, DEBUG=None):
        # pk = parent key
        for keyID in range(0, len(thislist)):
            key = thislist[keyID]
            if type(key) is dict:
                complexstatements = {}
                staID = BNode()
                staIDlocal = BNode()
                for k, v in key.items():
                    #root="%s/%s" % (self.RootRef, pk)
                    root = self.SetRef(pk)
                    #kRef = "%s/%s" % (self.RootRef, k)
                    self.dictcontent.append({"list": root, self.SetRef(k): v, 'type': type(v), 'sort': keyID })                    
                    if type(v) is str:
                        complexstatements[URIRef(self.SetRef(k))] = v
                        self.g.add((staIDlocal, URIRef(self.SetRef(k)), Literal(v)))                        
                    elif type(v) is list:
                        complexarray = []
                        for item in v:
                            complexarray.append({ self.SetRef(k): item, URIRef("%s#Vocabulary" % self.SetRef(k)) : "url" })
                            # Create and add a new statement
                            staIDar = BNode()
                            self.g.add((staIDar, URIRef(self.SetRef(k)), Literal(item)))
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
    
    def rotate(self, thisdict, pk, DEBUG=None):
        self.cmdiloc = {}        
        
        if (isinstance(thisdict,list)):
            #root="%s/%s" % (self.RootRef, pk)
            root = self.SetRef(pk)
            #kRef = "%s/%s" % (self.RootRef, k)
            self.dictcontent.append({"list": root, self.SetRef(k): v })
            self.g.add((URIRef(root), URIRef(self.SetRef(k)), Literal(v)))
            return
                
        for k,v in thisdict.items():
            if (isinstance(v,dict)):
                if pk:
                    fullXpath = "%s/%s" % (pk, k)
                else:
                    fullXpath = k
                self.namespaces[self.SetRef(pk)] = k.lower()
                if DEBUG:
                    print("XPath %s [%s]" % (fullXpath, k))
                self.rotate(v, fullXpath)
                ###self.rotate(v, k)
                #root="%s%s" % (self.RootRef, pk)
                root = self.SetRef(pk)
                #kRef = "%s/%s" % (self.RootRef, k)
                staID = BNode()
                staID = URIRef(self.RootRef)
                self.g.add((staID, URIRef(root), URIRef(self.SetRef(k))))
                self.locator[root] = staID
                continue    
            else:
                if (isinstance(v,list)):
                    print(k)
                    self.rotatelist(v, k)
                    continue
                
                #root="%s%s" % (self.RootRef, pk)
                root = self.SetRef(pk)
                #kRef = "%s/%s" % (self.RootRef, k)
            
                if self.SetRef(k) in self.cmdiloc:
                    cache = self.cmdiloc['root']
                    if type(cache) is list:
                        cache.append( { self.SetRef(k): v })
                    else:
                        cache = { self.SetRef(k): v }
                else:
                    self.cmdiloc = { self.SetRef(k): v }
                self.dictcontent.append({"parent": root, self.SetRef(k): v, 'type': type(v) })
                
                # Add statement
                staID = BNode()                
                self.locator[URIRef(self.SetRef(k))] = staID
                self.g.add((URIRef(root), URIRef(self.SetRef(k)), Literal(v)))

        self.setNamespaces()
        return self.dictcontent

    def statements(self, limit=False, DEBUG=False):
        allstatements = []
        for subj, pred, obj in self.g:
            localstatements = [ subj, pred, obj ] 
            allstatements.append(localstatements)
        return allstatements
    
    def graph_to_turtle(self, DEBUG=False):
        v = self.g.serialize(format='n3')
        statements = str(v) 
        statements = statements.replace('\\n', "\n")
        return statements  

    def dataset_upload(self, ROOT, DATAVERSE_ID, API_TOKEN, filename):
        headers = { "X-Dataverse-key" : API_TOKEN, 'Content-Type' : 'application/json-ld'}
        url = "%s/%s" % (ROOT, "api/dataverses/%s/datasets" % DATAVERSE_ID)
        r = requests.post(url, data=open(filename, 'rb'), headers=headers)
        return r.text          
