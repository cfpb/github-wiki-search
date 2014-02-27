from universalclient import Client
from bs4 import BeautifulSoup as BS
import requests
import settings
from urlparse import urlparse
import urllib
import json

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


class ES(object):
    github = GitEvents()
    def create_bulk_data(self, urls):
        bulk_data_obj = []
        for url in urls:
            html = requests.get(url).content
            soup = BS(html, 'lxml')
            path = urlparse(url).path[1:]
            repo_name = '/' + '/'.join(path.split('/')[:2])
            page_id = urllib.quote(path, '')  # remove initial slash
            bulk_data_obj.append({ 
                "index": {
                    "_index": "wiki", "_type": "page", "_id": page_id
            }})
            bulk_data_obj.append({
                'url': url,
                'title': unicode(soup.find(id='head').h1.text),
                'content': unicode(soup.find(id='wiki-content')),
                'repo': repo_name
            })
        bulk_data = '\n'.join([json.dumps(row) for row in bulk_data_obj]) + '\n'
        return bulk_data
    def update_indices(self):
        """
        update all wikis that have changed since last call to update_indices
        """
        changed_urls = self.github.get_changed_page_urls()
        bulk_data = self.create_bulk_data(changed_urls)
        resp = requests.post(settings.ES_HOST + '/_bulk', data=bulk_data)
        requests.post(settings.ES_HOST + '/_refresh')
        return resp

    def index_new_repo(self, repo_name):
        """
        repo_name format '<organization>/<repo>'
        """
        list_url = '/'.join([settings.GITHUB_HOST, repo_name, 'wiki/_pages'])
        list_html = requests.get(list_url).content
        soup = BS(list_html, 'lxml')
        paths = [x.get('href') for x in soup.find(id='wiki-content').ul.find_all('a')]
        urls = [settings.GITHUB_HOST + path for path in paths]
        bulk_data = self.create_bulk_data(urls)
        with open('bulk_data.txt', 'w') as f:
            f.write(bulk_data)
        resp = requests.post(settings.ES_HOST + '/_bulk', data=bulk_data)
        requests.post(settings.ES_HOST + '/_refresh')
        return resp
# es = ES()
# es.index_new_repo('mbates/Design-DevRegroup')
#r = es.incremental_update_wiki()

