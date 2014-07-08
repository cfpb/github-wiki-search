#! /usr/bin/python
from universalclient import Client
from bs4 import SoupStrainer, BeautifulSoup as BS
import settings
from urlparse import urlparse
import urllib
import json
from datetime import datetime
import gevent
from gevent import monkey
from gevent.pool import Pool
import itertools

pool = Pool(50)

# patches stdlib (including socket and ssl modules) to cooperate with other greenlets
monkey.patch_all()

import urllib2
from os import path
from os.path import join as path_join

DIR = path.dirname(path.realpath(__file__))
LOG = path_join(DIR, '..', 'client', 'dist', 'log')

es_client = Client(settings.ES_HOST)
gh_client = Client(settings.GITHUB_HOST)
gh_api_client = gh_client.api.v3

def index_all_repos():
    """
    index all repos, reset elasticsearch, rebuild elasticsearchindices
    """
    start_time = datetime.now()
    repo_names = (repo['full_name'] for page in _get_paginated_repos() for repo in page)

    jobs = [pool.spawn(index_repo, repo_name) for repo_name in repo_names]
    gevent.joinall(jobs)
    repo_data = [job.value for job in jobs]
    bulk_rows = (row for item in repo_data for row in item['bulk_rows'])
    bulk_rows = itertools.chain(bulk_rows, index_all_users(repo_data))
    bulk_data = '\n'.join([json.dumps(row) for row in bulk_rows]) + '\n'

    print "writing bulk data"
    with open(path_join(DIR, 'bulk_data.txt'), 'w') as f:
        f.write(bulk_data)

    # reset index
    es_client.wiki.delete()
    es_client.autocomplete.delete()
    with open(path_join(DIR, 'schema', 'page.json'), 'r') as schema_page:
        es_client.wiki.post(data=schema_page.read())
    with open(path_join(DIR, 'schema', 'autocomplete.json'), 'r') as schema_auto:
        es_client.autocomplete.post(data=schema_auto.read())
    resp = es_client._bulk.post(data=bulk_data)
    es_client._refresh.post()
    print 'total time:', datetime.now() - start_time
    return resp


def _get_paginated_repos():
    """
    generate paginated list of all repos in the enterprise github system
    """
    last_repo_id = 0
    while last_repo_id is not None:
        print last_repo_id
        params={"since": last_repo_id}
        repos = gh_api_client.repositories.get(params=params).json()
        last_repo_id = repos[-1]['id'] if repos else None
        if last_repo_id:
            yield repos

def index_repo(repo_name):
    """ 
    return a dict of {'user', 'page_count', 'bulk_rows'}
    for the given repo_name
    """
    bulk_rows = index_wiki(repo_name)

    # add autocomplete data for repo
    page_count = len(bulk_rows)/2
    user, repo = repo_name.split('/')
    repo_id = urllib.quote(repo_name, '')

    bulk_rows += [{ 
        "index": {
            "_index": "autocomplete", "_type": "repo", "_id": repo_id
    }},
    {
        'owner': user,
        'repo': repo,
        'count': page_count
    }]

    return {'user': user, 'page_count':page_count, 'bulk_rows': bulk_rows}

def index_wiki(repo_name):
    """ return bulk update rows for wiki for repo_name repo """
    # get and parse a list of all wiki page urls
    url_template = '%s/%s/wiki/_pages'
    url = url_template % (settings.GITHUB_HOST, repo_name)
    html = urllib2.urlopen(url).read()
    strainer = SoupStrainer(id='wiki-content')
    soup = BS(html, 'lxml', parse_only=strainer)
    if not soup.ul:
        return []
    page_links = soup.ul.find_all('a')
    page_urls = (settings.GITHUB_HOST + link.get('href') for link in page_links)

    # index each page
    jobs = [pool.spawn(index_wiki_page, repo_name, page_url) for page_url in page_urls]
    gevent.joinall(jobs)

    return [row for job in jobs for row in job.value]

def index_wiki_page(repo_name, page_url):
    html = urllib2.urlopen(page_url).read()
    strainer = SoupStrainer(id='wiki-wrapper')
    soup = BS(html, 'lxml', parse_only=strainer)
    path = urlparse(page_url).path[1:]
    page_id = urllib.quote(path, '')  # remove initial slash
    return ({ 
        "index": {
            "_index": "wiki", "_type": "page", "_id": page_id
    }},
    {
        'url': page_url,
        'title': ' '.join(soup.find(id='head').h1.findAll(text=True)),
        'content': ' '.join(soup.find(id='wiki-content').findAll(text=True)),
        'repo': '/' + repo_name
    },)

def index_all_users(repo_data):
    """ 
    given a lst of repo_data containing page_count and user for each repo
    retur bulk_rows for user autocomplete
    """
    users = {}
    for item in repo_data:
        users.setdefault(item['user'], 0)
        users[item['user']] += item['page_count']

    bulk_rows = []
    for user, page_count in users.items():
            bulk_rows.append({ 
                "index": {
                    "_index": "autocomplete", "_type": "user", "_id": user
            }})
            bulk_rows.append({
                'owner': user,
                'count': page_count
            })
    return bulk_rows

if __name__ == "__main__":
    index_all_repos()
    with open(LOG, 'a') as log:
        log.write('%s - synced\n' % datetime.utcnow().isoformat())
