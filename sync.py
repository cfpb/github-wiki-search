#! /usr/bin/python
from universalclient import Client
from bs4 import SoupStrainer, BeautifulSoup as BS
import requests
import settings
from urlparse import urlparse
import urllib
import json
import re
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
print DIR, path.join(DIR, 'bulk_data.txt')

es_client = Client(settings.ES_HOST)
gh_client = Client(settings.GITHUB_HOST)
gh_api_client = gh_client.api.v3.repositories

whitespace_re = re.compile(r'(\W|\n)+')
def extract_text_from_html(soup):
    text_nodes = soup.findAll(text=True)
    text_with_newlines = ' '.join(text_nodes)
    text = whitespace_re.sub(' ', text_with_newlines)
    return text

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

class GitEvents(object):
    client = Client(settings.GITHUB_HOST + '/api/v3/events')
    # the etag for the last call to github
    etag = ''
    # the last event id to be pulled from github
    last_event = None
    def get_page_of_events(self, page=1, etag=True):
        """
        return a page (1-10) of events. if etag is True, will check
        etag version
        """
        headers = {'If-None-Match': self.etag} if etag else {}
        resp = self.client.get(headers=headers, params={"page": page})
        if etag:
            self.etag = resp.headers.get('ETag', self.etag)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 304:
            return []

    def get_changed_page_urls(self):
        """
        return the urls for all pages changed since the last
        time get_changed_page_urls was called. Uses a combination
        of etag and the last synced event id to minimize (hopefully
        eliminate) duplication.
        """
        data = self.get_page_of_events()
        if not data:
            return data
        newest_last_event = int(data[0]['id'])
        intermediate_last_event = int(data[-1]['id'])
        pages = range(2, 11)
        for page in pages:
            if intermediate_last_event <= self.last_event:
                break
            data += self.get_page_of_events(page=page, etag=False)
            intermediate_last_event = int(data[-1]['id'])

        #get the pages changed for gollumEvents that happened after the last sync
        page_lists = [event['pages'] for event in data if event['type'] == 'gollumEvent' and int(event['id']) > self.last_event]
        # each event can have multiple pages changed, so flatten
        pages = [item for sublist in page_lists for item in sublist] # flatten the lists of pages

        urls = [page['html_url'] for page in pages]
        urls = list(set(urls)) # dedup
        # update the last_event counter
        self.last_event = newest_last_event
        return urls

def _repo_pages():
    """
    generate pages of all repos in the repository
    """
    last_repo_id = 0
    while last_repo_id is not None:
        print last_repo_id
        params={"since": last_repo_id}
        repos = gh_api_client.get(params=params).json()
        last_repo_id = repos[-1]['id'] if repos else None
        if last_repo_id:
            yield repos
        last_repo_id = None

class ES(object):
    github = GitEvents()
    def _create_bulk_data(self, urls):
        """
        given a list of urls, get the index data and return
        in the bulk upload format
        """
        print "generating bulk data for urls"
        bulk_data_obj = []

        jobs = [pool.spawn(_get_soup, url, 'wiki-wrapper') for url in urls]
        gevent.joinall(jobs)
        soups = [job.value for job in jobs]

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

    def sync_indices(self):
        """
        update all wikis that have changed since last call to update_indices
        """
        changed_urls = self.github.get_changed_page_urls()
        bulk_data = self._create_bulk_data(changed_urls)
        resp = es_client._bulk.post(data=bulk_data)
        es_client._refresh.post()
        return resp

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
        repo_names = (repo['full_name'] for page in _repo_pages() for repo in page)
        url_template = '%s/%s/wiki/_pages'
        repo_urls = [url_template % (settings.GITHUB_HOST, repo) for repo in repo_names]
        jobs = [pool.spawn(_get_soup, url, 'wiki-content') for url in repo_urls]
        gevent.joinall(jobs)
        repo_soups = [job.value for job in jobs]
        repo_tuples = [(url, repo_name, path, soup.ul.find_all('a'),) for url, repo_name, path, soup in repo_soups if soup.ul]

        bulk_data = self._create_wiki_bulk_data(repo_tuples)
        bulk_data += self._create_autocomplete_bulk_data(repo_tuples)

        print "writing bulk data"
        with open(path_join(DIR, 'bulk_data.txt'), 'w') as f:
            f.write(bulk_data)

        # reset index
        es_client.wiki.delete()
        es_client.autocomplete.delete()
        with open(path_join(DIR, 'schema_page.json'), 'r') as schema_page:
            es_client.wiki.post(data=schema_page.read())
        with open(path_join(DIR, 'schema_autocomplete.json'), 'r') as schema_auto:
            es_client.autocomplete.post(data=schema_auto.read())
        resp = es_client._bulk.post(data=bulk_data)
        es_client._refresh.post()
        return resp

es = ES()

if __name__ == "__main__":
    es.index_all_repos()
