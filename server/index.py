#! /usr/bin/python
from universalclient import Client
import settings
import indexers
import time
from datetime import datetime
import indexers.github_helpers as helpers
import itertools
import gevent
from gevent import monkey
from gevent.pool import Pool
pool = Pool(50)
# patches stdlib (including socket and ssl modules) to cooperate with other greenlets
monkey.patch_all()

import urllib3

# monkeypatch response to always force https redirects - github redirects to http first, then to https; does not work with our connection pooler
# TODO: this isn't working
class HTTPResponse(urllib3.response.HTTPResponse):
    def get_redirect_location(self):
        import pdb
        pdb.set_trace()
        location = super(HTTPResponse, self).get_redirect_location()
        if location and location.startswith('http:'):
            location = 'https' + location[4:]
        return location
urllib3.response.HTTPResponse = HTTPResponse

pages_pool = urllib3.PoolManager(20)
ghe_pool = urllib3.connection_from_url(settings.GITHUB.get('GHE', {}).get('WEB'), maxsize=50, block=True)
gh_pool = urllib3.connection_from_url(settings.GITHUB.get('GH', {}).get('WEB'), maxsize=50, block=True)
ghe_api_client = Client(settings.GITHUB.get('GHE', {}).get('API')).api.v3
gh_api_client = Client(settings.GITHUB.get('GH', {}).get('API'))

helpers.create_index('history')
helpers.create_index('search')
helpers.create_index('autocomplete')

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
    return [repo['full_name'] for repo in iter_get(ghe_api_client.repositories) if not repo['fork']]

def _get_gh_org_repos(org_name):
    if not settings.GITHUB.get('GHE', {}).get('API'):
        return []
    return (repo['full_name'] for repo in iter_get(gh_api_client.orgs._(org_name).repos) if not repo['fork'])

def _get_gh_repos():
    if not settings.GITHUB.get('GH', {}).get('ORGS'):
        return []
    org_iters = [_get_gh_org_repos(org_name) for org_name in settings.GITHUB['GH']['ORGS']]
    return [repo_name for repo_name in itertools.chain(*org_iters)]

def index_ghe_repos(repo_names=None, force=False):
    repo_names = repo_names or _get_ghe_repos()
    jobs = [pool.spawn(indexers.wiki, 'GHE', repo_name, ghe_pool, force) for repo_name in repo_names]
    jobs += [pool.spawn(indexers.readme, 'GHE', repo_name, ghe_pool, force) for repo_name in repo_names]
    jobs = [pool.spawn(indexers.gh_pages, 'GHE', repo_name, pages_pool, force) for repo_name in repo_names]
    return jobs

def index_gh_repos(repo_names=None, force=False):
    repo_names = repo_names or _get_gh_repos()
    jobs = [pool.spawn(indexers.wiki, 'GH', repo_name, gh_pool, force) for repo_name in repo_names]
    jobs += [pool.spawn(indexers.readme, 'GH', repo_name, gh_pool, force) for repo_name in repo_names]
    jobs += [pool.spawn(indexers.gh_pages, 'GH', repo_name, pages_pool, force) for repo_name in repo_names]
    return jobs

if __name__ == '__main__':
    start = time.mktime(datetime.now().timetuple())
    jobs = index_ghe_repos(['CFPB/handbook', 'SES/ses-next'], True)
    jobs += index_gh_repos(['cfpb/django-nudge', 'cfpb/capital-framework'], True)
    gevent.joinall(jobs)
    end = time.mktime(datetime.now().timetuple())
    print 'Completed: (%s secs)' % (end-start)
