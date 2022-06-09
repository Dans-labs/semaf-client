import json
import requests
import re
from skosmos_client import SkosmosClient, SkosmosConcept
from config import * 

class Draftlinkage():
    def __init__(self, sourcename=None, sourceobject=None, content=None, debug=False):
        self.keywords = {}
        self.geoconcepts = {}
        self.source = sourceobject
        self.sourcename = sourcename
        self.linkagesource = LINKAGE_SOURCE
        self.apiskosmos = API_SKOSMOS
        self.wikicacheurl = WIKI_CACHE_URL
        self.debug = debug
        self.geosource = SKOSMOS_GEO_SOURCE

    def cache_wikidata(self, termURI):
        artnamespace = {}
        searchterm = re.search("(Q\w+)", termURI)

        if searchterm:
            cache_url = "%s/%s.json" % (self.wikicacheurl, str(searchterm.group(0)))
            artnamespace['term'] = searchterm.group(0)
            artnamespace['termURI'] = termURI
            try:
                r = requests.get(cache_url)
                concept = r.json()
                artnamespace['name'] = concept['entities'][searchterm.group(0)]['aliases']['en']
            except:
                artnamespace[termURI] = {}
        return artnamespace

    def geofilter(self, wikijson, name):
        for term in wikijson['data']['terms']:
            for x in term['result']['terms']:
                check = re.search(r"%s" % name, str(x['scopeNote']))
                if check:
                    if self.debug:
                        print("%s %s" % (x['uri'], x['scopeNote']))
                    for code in x['altLabel']:
                        if len(code) <= 3:
                            cache = self.cache_wikidata(x['uri'])
                            return { 'uri' : x['uri'], 'geocode': code, 'cache': cache }
                    cache = self.cache_wikidata(x['uri'])
                    return { 'uri' : x['uri'], 'cache': cache, 'geoname': x['scopeNote'] }
        return

    def conceptmaker(self, cotype, k, q, s):
        if cotype == 'nde':
            return self.ndegrapql(k, q, s)
        if cotype == 'skosmos':
            return self.skosmosql(k, q, s)
        return

    def skosmosql(self, field, q, s):
        results = {}
        #q = 'Yugoslavia'
        query = q + '*'
        skosmos = SkosmosClient(api_base=self.apiskosmos)
        results[field] = q
        results['source'] = self.sourcename
        results['rawdata'] = skosmos.search(query, vocabs=s, lang="en")
        concepturi = []
        for concept in results['rawdata']:
            if 'uri' in concept:
                payload = {'uri': concept['uri'], 'format': 'application/ld+json'}
                url = self.apiskosmos + s + '/data' 
                req = requests.get(url, params=payload)
                data = req.json()
                concepturi.append({ concept['uri']: data })

        results['uri'] = concepturi
        return results

    def ndegrapql(self, field, q, s):
        results = {}
        GEOFLAG = True
        headers = {"content-type":"application/json"}
        query = "{\"query\":\"query Terms {  terms(sources: [\\\"" + s + "\\\"], query: \\\"" + q + "\\\") {    source {      uri      name      creators {        uri        name        alternateName      }    }    result {      __typename      ... on Terms {        terms {          uri          prefLabel          altLabel          hiddenLabel          scopeNote          broader {            uri            prefLabel          }          narrower {            uri            prefLabel          }          related {            uri            prefLabel          }        }      }      ... on Error {        message      }    }  }}\"}"
        r = requests.post(NDE_GRAPHQL, data=query, headers=headers)
        results['rawdata'] = r.json()
        results[field] = q
        results['source'] = self.sourcename
        try:
            geo = False
            for locentity in NL_wiki_locations_regexp:
                if not geo:
                    geo = self.geofilter(results['rawdata'], locentity)
            if geo:
                results['geo'] = geo
        except:
            GEOFLAG = False
        return results

    def linkage(self, x):
        if isinstance(x, list):
            return [self.linkage(v) for v in x]
        elif isinstance(x, dict):
            for k, v in x.items():
                if k == '1Keyword':
                    for keyword in v:
                        search = self.conceptmaker('nde', k, keyword, self.linkagesource)
                        if search:
                            if self.debug:
                                print("%s => %s\n" % (keyword, search))
                            self.keywords[keyword] = search
                if k in Specialfields:
                    concepts = {}
                    candidates = []
                    if type(v) is str:
                        candidates.append(v)
                    elif type(v) is list:
                        for i in range(len(v)):
                            candidates.append(v[i])

                    for value in candidates:
                        skossearch = self.conceptmaker('skosmos', k, value, self.geosource)
                        if skossearch:
                            concepts['skosmos'] = skossearch
                        search = self.conceptmaker('nde', k, value, self.linkagesource)
                        if search:
                            concepts['nde'] = search
                            if self.debug:
                                print("%s => %s\n" % (value, search))
                        self.geoconcepts[value] = concepts
            return {k[0].upper() + k[1:]: self.linkage(v) for k, v in x.items()}
        else:
            return x
