#!/usr/bin/python3

from Semaf import Semaf
from config import DATAVERSE_ROOT, DATAVERSE_EXPORT

datafile = 'harvard'
sm = Semaf()
#sm.loadfile(datafile, 'json-ld')
doi = 'doi:10.7910/DVN/FUSIWA'
sm.loadurl(doi, 'json-ld', DATAVERSE_ROOT, DATAVERSE_EXPORT)
sm.statements()
#print(sm.dumps())

# Edit statements in metadata
sm.edit_statement('keyword#Term', 'New Statement')
print(sm.dumps())

print(sm.locator('keyword#Term'))
print(sm.locator('terms/title'))
# Add new statements in metadata keywords

print(sm.graph_to_turtle())
