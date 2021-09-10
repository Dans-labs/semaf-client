from rdflib import Graph, URIRef, Literal, BNode, plugin
from rdflib.serializer import Serializer
from collections import defaultdict, OrderedDict
from xml.dom import minidom
from os import listdir
from os.path import isfile, join
import re
import sys
import json
import requests
import operator

class Semaf():
    def __init__(self, context=None, thisformat='json-ld', debug=False):
        self.stats = {}
        self.json = {}
        self.locators = {}

    def loadfile(self, filename=None, thisformat=None, parent=None):
        self.context = False
        with open(filename, encoding='utf-8') as fh:
            self.context = json.load(fh)
        self.g = Graph().parse(data=json.dumps(self.context), format=thisformat)
        return self.context

    def loadurl(self, doi=None, thisformat=None, url=None, export=None):
        URL = "%s/%s%s" % (url, export, doi)
        print(URL)
        self.context = json.loads(requests.get(URL).text)
        self.g = Graph().parse(data=json.dumps(self.context), format=thisformat)
        return self.context

    def dumps(self):
        return json.dumps(self.graph_to_jsonld(),indent=2)

    def filter(self, thisfilter=None, where=None, limit=False, DEBUG=False):
        self.statement = {}
        for subj, pred, obj in self.g:
            if re.search(thisfilter, pred):
                self.statement = [subj, pred, obj]
                if DEBUG:
                    print("%s %s %s" % (subj, pred, obj))
        return

    def statements(self, limit=False, DEBUG=False):
        allstatements = []
        for subj, pred, obj in self.g:
            localstatements = [ subj, pred, obj ] 
            allstatements.append(localstatements)
            if DEBUG:
                print("%s %s %s" % (subj, pred, obj))
            if re.search('keyword#Term', pred):
                self.locators['guid'] = subj
                self.locators['gupred'] = pred
            if re.search('citation/Keyword', pred):
                self.locators['keyguid'] = obj
                locs = {}
                self.locators['subject'] = subj
                self.locators['predicate'] = pred
                self.locators['citation/Keyword'] = locs
        return allstatements

    def locator(self, rootpredicate, DEBUG=False):
        locs = {}
        for subj, pred, obj in self.g:
            if re.search(rootpredicate, pred):
                locs['subject'] = subj
                locs['predicate'] = pred
                locs['object'] = obj
                self.locators[rootpredicate] = locs
        return locs

    def edit_statement(self, locsubject, newobject):     
        locators = {}
        for subj, pred, obj in self.g:
            if re.search(locsubject, pred):
                locators['subject'] = subj
                locators['predicate'] = pred
        # For example, g.add((guid, gupredurl, Literal('https://www.wikidata.org/wiki/Q1935049')))
        self.g.set((locators['subject'], locators['predicate'], Literal(newobject)))
        return

    def add_statement(self, statements=False):
        staID = BNode()

        for k,v in statements.items():
            locurl = "%s%s" % ('https://dataverse.org/schema/citation/', k)
            locurlRef = URIRef(locurl)
            self.g.add((staID, locurlRef, Literal(v)))

        # root = citation/Keyword
        rootnode = statements['rootnode']
        self.g.add((self.locators[rootnode]['subject'], self.locators[rootnode]['predicate'], staID))
        return 

    def serialize(self, filename, thisformat):
        v = g.serialize(destination=filename, format=thisformat)
        return

    def graph_to_turtle(self, DEBUG=False):
        v = self.g.serialize(format='n3')
        statements = str(v) 
        statements = statements.replace('\\n', "\n")
        return statements

    def graph_to_jsonld(self, DEBUG=False): 
        v = self.g.serialize(format='json-ld')
        o = json.loads(v, object_pairs_hook=OrderedDict)
        self.items = {}
        for i in range(0, len(o)):
            item = o[i]
            thiskey = o[i]['@id']
            del item['@id']
            self.items[thiskey] = item
        self.records = defaultdict(list)

        for i in range(0, len(o)):
            item = o[i]
            if re.search('terms\/title', str(item)):
                #print("%s %s" % (i, item))
                indexblock = i

        # Delete internal id
        if '@id' in o[indexblock]:
            del o[indexblock]['@id']
            #del o[indexblock]['@type']

        for ikey in o[indexblock]:
            #print("%s %s [%s]" % (ikey, type(o[0][ikey]), len(o[0][ikey])))
            for element in o[indexblock][ikey]:
                fullrecord = ''
                #print("%s %s" % (ikey, element))
                if '@id' in element:
                    fullrecord = self.items[element['@id']]

                #print(fullrecord)
                if fullrecord:
                    if ikey in self.records:
                        #print(type(records[ikey]))
                        if not type(self.records[ikey]) is list:
                            thisrecord = [ self.records[ikey] ]
                        else:
                            thisrecord = self.records[ikey] 
                        thisrecord.append(fullrecord)
                        self.records[ikey] = thisrecord 
                        #records[ikey] = fullrecord
                    else:
                        self.records[ikey] = fullrecord  
                else:
                    if ikey in self.records:
                        #print("Check %s" % type(records[ikey]))
                        if not type(self.records[ikey]) is list: 
                            thisrecord = [ element ] 
                            self.records[ikey] = thisrecord
                        else:
                            thisrecord = element
                        thisrecord.append(fullrecord)
                        #records[ikey] = thisrecord
                        self.records[ikey] = element
                    else:
                        self.records[ikey] = element
        return self.records
        
