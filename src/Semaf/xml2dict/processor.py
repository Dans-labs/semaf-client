import sys
from xml.dom import minidom
from os import listdir
from os.path import isfile, join
import json
from bs4 import BeautifulSoup
from bs2json import bs2json
import operator

class CMDI():
    def __init__(self, actions=None, url=None, content=None, debug=False):
        self.url = url
        self.stats = {}
        self.json = {}
        self.hierarchy = {}
        self.DEBUG = False
        self.control = actions
        self.metadata = {}
        self.path = []
        self.schema = {}
        self.currentkey = ''
        if 'verbose' in actions:
            self.DEBUG = actions['verbose']

    def traverse(self, artefact, parent=None):
        # vty
        #print(type(artefact))
        if type(artefact) is dict:
            if self.DEBUG:
                print("[KEY DEBUG] Keys: %s " % str(artefact.keys()))

            for key in artefact.keys():
                showkey = key
                if parent:
                    showkey = "%s/%s" % (parent, key) 
                if 'hierarchy' in self.control:
                    print("\t /%s" % showkey)
                self.currentkey = showkey
                #if self.DEBUG:
                #print("%s KEY %s %s" % (artefact[key], key, self.currentkey))
                self.traverse(artefact[key], showkey) 
        elif type(artefact) is list:
            for listkey in artefact:
                if self.DEBUG:
                    print("Art %s %s %s" % (listkey, parent, type(listkey))) #, artefact[listkey]))
                showkey = listkey
                if parent:
                    showkey="%s/%s" % (parent, listkey)
                if 'hierarchy' in self.control:
                    print("\t\t /%s" % showkey)
                if not type(listkey) is str:
                    self.currentkey = showkey
                if self.DEBUG:
                    print("KEY %s %s" % (self.currentkey, type(listkey)))
                self.traverse(listkey, parent)
        else:
            DEBUG = 1
            if self.DEBUG:
                print("[DEBUG KEY-VALUE] %s %s" % (self.currentkey, artefact))
            item = {}
            item[self.currentkey] = artefact
            #self.path.append( { self.currentkey: artefact } )
            self.path.append(item)
            if artefact:
                self.metadata[self.currentkey] = artefact
            i = 1
        return
 
    def gethierarchy(self):
        print(self.json.keys())
        self.traverse(self.json)
        return

    def xpath(self):
        #print(self.json.keys())
        self.record = {}
        x = self.traverse(self.json)
        pkey = ''
        prevpath = ''
        for item in self.path:
            for key in item:
                value = item[key]
                semkey = key
                path = key.split('/')
                #semkey = semkey.replace('#document', 'https://cmdi.no/schema')
                if self.DEBUG:
                    print("%s %s" % (key, value))
                common = [value for value in path if value in prevpath]
                if key in self.record:
                    cache = self.record[key]
                    #print("%s %s" % (cache, type(cache)))
                    if type(cache) is list:
                        newcache.append(value)
                    else:
                        newcache = [ cache, value ] 
                    dictvalue = { 'value': newcache, 'prev': pkey }
                    self.record[semkey] = newcache # dictvalue # newcache
                else:
                    dictvalue = { 'value': value, 'prev': pkey, 'pathlen': len(path) } #, 'parent': '/'.join(common) }
                    self.record[semkey] = value #dictvalue
                pkey = key
                prevpath = pkey.split('/')
        return self.record

    def dappend(self, dictionary, key, item):
        """Append item to dictionary at key.  Only create a list if there is more than one item for the given key.
        dictionary[key]=item if key doesn't exist.
        dictionary[key].append(item) if key exists."""
        self.h = []
        if key in dictionary.keys():
            self.h.append(key)
            if not isinstance(dictionary[key], list):
                lst=[]
                lst.append(dictionary[key])
                lst.append(item)
                dictionary[key]=lst
            else:
                dictionary[key].append(item)
        else:
            self.h.append(key)
            dictionary.setdefault(key, item)
        #print("H: %s" % self.h)
        #print("%s=%s" % (key, item))

    def getstats(self, order=True):
        return sorted(self.stats.items(),key=operator.itemgetter(1),reverse=order)

    def printstats(self, order=True):
        for item in sorted(self.stats.items(),key=operator.itemgetter(1),reverse=order):
            print("%s %s" % (item[0], item[1]))
        return 

    def schema(self, order=True):
        for item in sorted(self.stats.items(),key=operator.itemgetter(1),reverse=order):
            #Availability    Availability    Other information on the geographic coverage of the data.               text    7               FALSE   FALSE   FALSE   FALSE   TRUE    TRUE    Access  cmm-cmdi
            print("\t%s\t%s\t%s description\t\ttext\t9\t\tFALSE\tFALSE\tFALSE\tFALSE\tTRUE\tTRUE\tcmm-cmdi\tcmm-cmdi" % (item[0], item[0], item[0]))
            #print("%s %s" % (item[0], item[1]))
        return

    def rowschema(self, order=True):
        for item in sorted(self.stats.items(),key=operator.itemgetter(1),reverse=order):
            self.schema[item[0]] = item[1]
            print("%s=%s" % (item[0], item[1]))
        return

    def node_attributes(self, node):
        """Return an attribute dictionary """
        if node.hasAttributes():
            return dict([(str(attr), str(node.attributes[attr].value)) for attr in node.attributes.keys()])
        else:
            return None

    def attr_str(self, node):
        return "%s-attrs" % str(node.nodeName)

    def hasAttributes(self, node):
        if node.nodeType == node.ELEMENT_NODE:
            if node.hasAttributes():
                return True
        return False

    def with_attributes(self, node, values):
        if node.nodeName in self.stats:
            self.stats[node.nodeName] = self.stats[node.nodeName] + 1
        else:
            self.stats[node.nodeName] = 1

        if self.hasAttributes(node):
            if isinstance(values, dict):
                self.dappend(values, '#attributes', self.node_attributes(node))
                return { str(node.nodeName): values }
            elif isinstance(values, str):
                return { str(node.nodeName): values,
                         self.attr_str(node): self.node_attributes(node)}
        else:
            return { str(node.nodeName): values }

    def xmldom2dict(self, node):
        """Given an xml dom node tree,
        return a python dictionary corresponding to the tree structure of the XML.
        This parser does not make lists unless they are needed.  For example:

        '12' becomes:
        { 'list' : { 'item' : ['1', '2'] } }
        BUT
        '1' would be:
        { 'list' : { 'item' : '1' } }

        This is a shortcut for a particular problem and probably not a good long-term design.
        """
        if not node.hasChildNodes():
            if node.nodeType == node.TEXT_NODE:
                if node.data.strip() != '':
                    return str(node.data.strip())
                else:
                    return None
            else:
                return self.with_attributes(node, None)
        else:
            #recursively create the list of child nodes            
            childlist=[self.xmldom2dict(child) for child in node.childNodes if (self.xmldom2dict(child) != None and child.nodeType != child.COMMENT_NODE)]
            #print(node.childNodes)
            #print(childlist)
            #for child in node.childNodes:
            #    print("type: %s" % child.nodeType)
            #    print(self.xmldom2dict(child))
            if len(childlist)==1:
                #print(node)
                return self.with_attributes(node, childlist[0])
            else:
                #if False not in [isinstance(child, dict) for child in childlist]:
                new_dict={}
                for child in childlist:
                    if isinstance(child, dict):
                        for k in child:
                            self.dappend(new_dict, k, child[k])
                    elif isinstance(child, str):
                        self.dappend(new_dict, '#text', child)
                    else:
                        print("ERROR")
                return self.with_attributes(node, new_dict)

    def loadfolder(self, fname):
        files = []
        self.content = {}
        onlyfiles = [f for f in listdir(fname) if isfile(join(fname, f))]
        for xmlfile in onlyfiles:
            files.append("%s/%s" % (fname, xmlfile))
        for filename in files:
            try:
                self.content[filename] = self.load(filename)
            except:
                print("Error in %s" % filename)
        return files

    def load(self, fname):
        self.json = self.xmldom2dict(minidom.parse(fname))
        return self.xmldom2dict(minidom.parse(fname))

    def loadhtml(self, fname):
        with open(fname, 'r') as file:
            data = file.read()
        S = BeautifulSoup(str(data), 'lxml')
        for script in S(["script", "style"]):
            script.extract()
        tag = S.find('html')
        converter = bs2json()
        self.json = converter.convert(tag)
        print(self.json)
        return self.json #self.xmldom2dict(minidom.parse(fname))

    def lispy_string(node, lst=None, level=0):
        if lst==None:
            lst=[]
        if not isinstance(node, dict) and not isinstance(node, list):
            lst.append(' "%s"' % node)
        elif isinstance(node, dict):
            for key in node.keys():
                lst.append("\n%s(%s" % (spaces(level), key))
                lispy_print(node[key], lst, level+2)
                lst.append(")")
        elif isinstance(node, list):
            lst.append(" [")
            for item in node:
                lispy_print(item, lst, level)
            lst.append("]")
        return lst

