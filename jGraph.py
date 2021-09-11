from xml.dom import minidom
import json
from Semaf import Semaf
from rdflib import Graph, URIRef, Literal, BNode, plugin, Namespace
from rdflib.serializer import Serializer
from collections import defaultdict, OrderedDict

class jGraph():
    def __init__(self, thisobject=None, RootRef=None, thisformat='json', debug=False):
        self.stats = {}
        self.json = {}
        self.context = json.loads(thisobject)
        self.RootRef = RootRef 
        self.dictcontent = []
        self.locator = {}
        self.EnrichFlag = False

        # Default Graph 
        self.g = Graph()

        # Define namespaces
        ns1 = Namespace("%s/" % self.RootRef)
        self.g.bind('cmdi', ns1)
        ns2 = Namespace("%s/#" % self.RootRef)
        self.g.bind('cmdidoc', ns2)
        ns3 = Namespace("%s/Keyword#" % self.RootRef)
        self.g.bind('keywords', ns3)
        
        # Second graph reservation 
        #self.gs = Graph()
        
    def rotatelist(self, thislist, pk, DEBUG=None):
        for keyID in range(0, len(thislist)):
            key = thislist[keyID]
            if type(key) is dict:
                complexstatements = {}
                staID = BNode()
                staIDlocal = BNode()
                for k, v in key.items():
                    root="%s/%s" % (self.RootRef, pk)
                    kRef = "%s/%s" % (self.RootRef, k)
                    self.dictcontent.append({"list": root, kRef: v, 'type': type(v), 'sort': keyID })                    
                    if type(v) is str:
                        complexstatements[URIRef(kRef)] = v
                        self.g.add((staIDlocal, URIRef(kRef), Literal(v)))                        
                    elif type(v) is list:
                        complexarray = []
                        for item in v:
                            complexarray.append({ kRef: item, URIRef("%s#Vocabulary" % kRef) : "url" })
                            # Create and add a new statement
                            staIDar = BNode()
                            self.g.add((staIDar, URIRef(kRef), Literal(item)))
                            if self.EnrichFlag:
                                self.g.add((staIDar, URIRef("%s#Vocabulary" % kRef), Literal('vccabulary name')))
                                self.g.add((staIDar, URIRef("%s#VocabularyURL" % kRef), Literal("http link to concept URI for %s" % item)))
                            # Add statements from array
                            self.g.add((staIDlocal, URIRef(kRef), staIDar)) 
                        complexstatements[URIRef(kRef)] = complexarray
                    if DEBUG:
                        print(complexstatements)
                self.g.add((URIRef(root), URIRef(kRef), staIDlocal))
        return
    
    def rotate(self, thisdict, pk, DEBUG=None):
        self.cmdiloc = {}        
        
        if (isinstance(thisdict,list)):
            root="%s/%s" % (self.RootRef, pk)
            kRef = "%s/%s" % (self.RootRef, k)
            self.dictcontent.append({"list": root, kRef: v })
            self.g.add((URIRef(root), URIRef(kRef), Literal(v)))
            return
                
        for k,v in thisdict.items():
            if (isinstance(v,dict)):
                self.rotate(v, k)
                root="%s/%s" % (self.RootRef, pk)
                kRef = "%s/%s" % (self.RootRef, k)
                staID = BNode()
                staID = URIRef(self.RootRef)
                self.g.add((staID, URIRef(root), URIRef(kRef)))
                self.locator[root] = staID
                continue    
            else:
                if (isinstance(v,list)):
                    print(k)
                    self.rotatelist(v, k)
                    continue
                
                root="%s/%s" % (self.RootRef, pk)
                kRef = "%s/%s" % (self.RootRef, k)
            
                if kRef in self.cmdiloc:
                    cache = self.cmdiloc['root']
                    if type(cache) is list:
                        cache.append( { kRef: v })
                    else:
                        cache = { kRef: v }
                else:
                    self.cmdiloc = { kRef: v }
                self.dictcontent.append({"parent": root, kRef: v, 'type': type(v) })
                
                # Add statement
                staID = BNode()                
                self.locator[URIRef(kRef)] = staID
                self.g.add((URIRef(root), URIRef(kRef), Literal(v)))

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
