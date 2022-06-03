#!/usr/bin/python3

import requests
from config import ROOT, DATAVERSE_ID, API_TOKEN

def dataset_upload(ROOT, DATAVERSE_ID, API_TOKEN, filename):
    headers = { "X-Dataverse-key" : API_TOKEN, 'Content-Type' : 'application/json-ld'}
    url = "%s/%s" % (ROOT, "api/dataverses/%s/datasets" % DATAVERSE_ID)
    r = requests.post(url, data=open(filename, 'rb'), headers=headers)
    return r.text

filename = '/tmp/test-metadata.json'
status = dataset_upload(ROOT, DATAVERSE_ID, API_TOKEN, filename)
print(status)
