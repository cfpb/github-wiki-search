from server import settings
import requests
from urlparse import urljoin

def index():
    bulk_data = []
    bulk_data += index_users(urljoin(settings.GITHUB['GHE']['API'], 'users'))
    for org in settings.GITHUB['GH']['ORGS']:
        bulk_data += index_users('https://api.github.com/orgs/{}/members?per_page=9999'\
            .format(org))
    return bulk_data

def index_users(url):
    r = requests.get(url)
    bulk_data_obj = []
    for person in r.json():
        bulk_data_obj.append({
            "index": {
                "_index": "autocomplete", 
                "_type": "user", 
                "_id": person['html_url']
        }})
        bulk_data_obj.append({
            'owner': person['login']
        })
    return bulk_data_obj