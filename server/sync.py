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


def _get_soup(url, id):
    """
    return generator that given a url, gets the content, parses it and
    returns a tuple of the urle, the repo name,  and the soup of the tag
    with the given id
    """
    html = urllib2.urlopen(url).read()
    strainer = SoupStrainer(id=id)
    soup = BS(html, 'lxml', parse_only=strainer)
    path = urlparse(url).path[1:]
    repo_name = '/' + '/'.join(path.split('/')[:2])

    return (url, repo_name, path, soup)

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


class ES(object):

    def _create_bulk_data(self, urls):
        """
        given a list of urls, get the index data and return
        in the bulk upload format
        """
        print "generating bulk data for urls"
        bulk_data_obj = []

        jobs = [pool.spawn(_get_soup, url, 'wiki-wrapper') for url in urls]
        gevent.joinall(jobs)
        soups = (job.value for job in jobs)

        for url, repo_name, path, soup in soups:
            page_id = urllib.quote(path, '')  # remove initial slash
            bulk_data_obj.append({ 
                "index": {
                    "_index": "wiki", "_type": "page", "_id": page_id
            }})
            bulk_data_obj.append({
                'url': url,
                'title': ' '.join(soup.find(id='head').h1.findAll(text=True)),
                'content': ' '.join(soup.find(id='wiki-content').findAll(text=True)),
                'repo': repo_name
            })
        bulk_data = '\n'.join([json.dumps(row) for row in bulk_data_obj]) + '\n'

        return bulk_data

    def _create_wiki_bulk_data(self, repo_tuples):
        page_links = (link for tpl in repo_tuples for link in tpl[3])
        page_urls = (settings.GITHUB_HOST + link.get('href') for link in page_links)
        bulk_data = self._create_bulk_data(page_urls)
        return bulk_data

    def _create_autocomplete_bulk_data(self, repo_tuples):
        users = {}
        repos = {}
        for url, repo_name, path, links in repo_tuples:
            page_count = len(links)
            user = repo_name.split('/')[1]
            users.setdefault(user, 0)
            users[user] += page_count
            repos[repo_name] = page_count

        bulk_data_obj = []
        for user, page_count in users.items():
            bulk_data_obj.append({ 
                "index": {
                    "_index": "autocomplete", "_type": "user", "_id": user
            }})
            bulk_data_obj.append({
                'owner': user,
                'count': page_count
            })
        for repo, page_count in repos.items():
            repo_id = urllib.quote(repo[1:], '')  # remove initial slash
            bulk_data_obj.append({ 
                "index": {
                    "_index": "autocomplete", "_type": "repo", "_id": repo_id
            }})
            bulk_data_obj.append({
                'owner': repo.split('/')[1],
                'repo': repo.split('/')[2],
                'count': page_count
            })
        bulk_data = '\n'.join([json.dumps(row) for row in bulk_data_obj]) + '\n'
        return bulk_data

    def index_all_repos(self):
        """
        sync all repositories in github enterprise
        """
        repo_names = (repo['full_name'] for page in _get_paginated_repos() for repo in page)
        url_template = '%s/%s/wiki/_pages'
        repo_urls = [url_template % (settings.GITHUB_HOST, repo) for repo in repo_names]
        jobs = [pool.spawn(_get_soup, url, 'wiki-content') for url in repo_urls]
        gevent.joinall(jobs)
        repo_soups = (job.value for job in jobs)
        repo_tuples = [(url, repo_name, path, soup.ul.find_all('a'),) for url, repo_name, path, soup in repo_soups if soup.ul]

        bulk_data = self._create_wiki_bulk_data(repo_tuples)
        bulk_data += self._create_autocomplete_bulk_data(repo_tuples)

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
        return resp

es = ES()

if __name__ == "__main__":
    es.index_all_repos()
    with open(LOG, 'a') as log:
        log.write('%s - synced\n' % datetime.utcnow().isoformat())
