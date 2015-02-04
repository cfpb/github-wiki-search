#! /usr/bin/python
from universalclient import Client
import settings
import indexers
from multiprocessing import Pool

es_client = Client(settings.ES_HOST)
gh_client = Client(settings.GITHUB_HOST)

gh_api_client = gh_client.api.v3

es_client.history.post()



def iter_get(client):
    """
    return an iterator over all results from GETing the client and any subsequent pages.
    """
    items = []
    while items or client:
        if not items:
            resp = client.get()
            items = resp.json()
            next = resp.links.get('next', {}).get('url')
            client = client._path([next]) if next else None
        if items:
            yield(items.pop(0))

def _get_ghe_repos():
    return iter_get(gh_api_client.repositories)

def index_gh_repos():
    p = Pool(20)
    for repo in _get_ghe_repos():
        if repo['has_wiki']:
            pass
