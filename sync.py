from universalclient import Client
from bs4 import SoupStrainer, BeautifulSoup as BS
import requests
import settings
from urlparse import urlparse
import urllib
import json
import re
import gevent
import grequests
from gevent import monkey
from gevent.pool import Pool

pool = Pool(50)

# patches stdlib (including socket and ssl modules) to cooperate with other greenlets
monkey.patch_all()

import urllib2


whitespace_re = re.compile(r'(\W|\n)+')
def extract_text_from_html(soup):
    text_nodes = soup.findAll(text=True)
    text_with_newlines = ' '.join(text_nodes)
    text = whitespace_re.sub(' ', text_with_newlines)
    return text

def _get_soup(url, id):
    """
    return generator that given a url, gets the content, parses it and
    returns a tuple of the url and the soup of the tag with the given id
    """
    html = urllib2.urlopen(url).read()
    strainer = SoupStrainer(id=id)
    soup = BS(html, 'lxml', parse_only=strainer)
    return (url, soup)

def _get_soups(id, urls):
    """
    return generator that given a url, gets the content, parses it and
    returns a tuple of the url and the soup of the tag with the given id
    """
    reqs = (grequests.get(url) for url in urls)
    resps = grequests.map(reqs, size=20)
    htmls = ((resp.request.url, resp.content,) for resp in resps)
    strainer = SoupStrainer(id=id)
    soups = ((url, BS(html, 'lxml', parse_only=strainer),) for url, html in htmls)
    return soups

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
        repos = requests.get(settings.GITHUB_HOST + '/api/v3/repositories', params=params).json()
        last_repo_id = repos[-1]['id'] if repos else None
        if last_repo_id:
            yield repos

class ES(object):
    github = GitEvents()
    def create_bulk_data(self, urls):
        """
        given a list of urls, get the index data and return
        in the bulk upload format
        """
        print "generating bulk data for %s urls" % len(urls)
        bulk_data_obj = []

        jobs = [pool.spawn(_get_soup, url, 'wiki-wrapper') for url in urls]
        gevent.joinall(jobs)
        soups = [job.value for job in jobs]

        for [url, soup], count in zip(soups, range(len(urls))):
            if not count % 100:
                print 'url: ', count
            path = urlparse(url).path[1:]
            repo_name = '/' + '/'.join(path.split('/')[:2])
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
        print "writing bulk data"
        with open('bulk_data.txt', 'w') as f:
            f.write(bulk_data)
        return bulk_data

    def sync_indices(self):
        """
        update all wikis that have changed since last call to update_indices
        """
        changed_urls = self.github.get_changed_page_urls()
        bulk_data = self.create_bulk_data(changed_urls)
        resp = requests.post(settings.ES_HOST + '/_bulk', data=bulk_data)
        requests.post(settings.ES_HOST + '/_refresh')
        return resp

    def index_page_of_repos(self, repo_id=None):
        """
        index all wiki pages for all repos in one page of repos returned by github api (100 repos)
        returns the id of the last repo synced.
        """
        params={"since": repo_id} if repo_id is not None else {}
        repos = requests.get(settings.GITHUB_HOST + '/api/v3/repositories', params=params).json()
        repo_names = [repo['full_name'] for repo in repos]
        self.index_new_repos(*repo_names)
        return repos[-1]['id'] if repos else None

    def index_all_repos(self):
        """
        sync all repositories in github enterprise
        """
        repo_names = (repo['full_name'] for page in _repo_pages() for repo in page)
        url_template = '%s/%s/wiki/_pages'
        repo_urls = (url_template % (settings.GITHUB_HOST, repo) for repo in repo_names)

        jobs = [pool.spawn(_get_soup, url, 'wiki-content') for url in repo_urls]
        gevent.joinall(jobs)
        repo_soups = [job.value for job in jobs]
#        repo_soups = _get_soups('wiki-content', repo_urls)
        page_paths = (soup.ul.find_all('a') for url, soup in repo_soups if soup.ul)
        page_urls = [settings.GITHUB_HOST + link.get('href') for sublist in page_paths for link in sublist]
        with open('page_urls.txt', 'w') as f:
            json.dump(page_urls, f)
        bulk_data = self.create_bulk_data(page_urls)
        resp = requests.post(settings.ES_HOST + '/_bulk', data=bulk_data)
        requests.post(settings.ES_HOST + '/_refresh')
        return resp

    def get_all_wiki_urls_for_repo(self, repo_name):
        """
        given a repo_name, return a list of all wiki pages for the repo.
        """
        list_url = '/'.join([settings.GITHUB_HOST, repo_name, 'wiki/_pages'])
        list_html = requests.get(list_url).content
        soup = BS(list_html, 'lxml')
        try:
            paths = [x.get('href') for x in soup.find(id='wiki-content').ul.find_all('a')]
        except AttributeError:
            paths = []
        urls = [settings.GITHUB_HOST + path for path in paths]
        print "%s: %s" % (repo_name, len(urls))
        return urls

    def index_new_repos(self, *repo_names):
        """
        Index all wiki pages for the list of repo_names
        repo_name format '<organization>/<repo>'
        """
        url_lists = [self.get_all_wiki_urls_for_repo(repo_name) for repo_name in repo_names]
        urls = [item for sublist in url_lists for item in sublist] # flatten
        bulk_data = self.create_bulk_data(urls)

        resp = requests.post(settings.ES_HOST + '/_bulk', data=bulk_data)
        requests.post(settings.ES_HOST + '/_refresh')
        return resp

es_client = ES()
# es.index_new_repo('mbates/Design-DevRegroup')
#r = es.incremental_update_wiki()

