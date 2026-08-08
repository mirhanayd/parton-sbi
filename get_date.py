import urllib.request, json
req = urllib.request.Request('https://inspirehep.net/api/literature?q=arxiv:1708.00911', headers={'Accept': 'application/json'})
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read())
    metadata = data['hits']['hits'][0]['metadata']
    if 'imprints' in metadata:
        print(metadata['imprints'][0].get('date', 'no date in imprint'))
    else:
        print(metadata.get('preprint_date', 'no preprint_date'))
