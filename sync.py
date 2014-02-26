from universalclient import Client
from bs4 import BeautifulSoup as BS
import requests
import settings
from urlparse import urlparse
import urllib
import json

class GitEvents(object):
    client = Client(settings.GITHUB_HOST + '/api/v3/events')
    etag = ''
    last_event = None
    def get_events(self):
        resp = self.client.get(headers={'If-None-Match': self.etag})
        self.etag = resp.headers.get('ETag', self.etag)
        if resp.status_code == 200:
            out = []
            for event in resp.json():
                if event['type'] != 'GollumEvent':
                    continue
                event_data = {
                    'url': event['payload']['pages'][0]['html_url'],
                    'title': event['payload']['pages'][0]['title'],
                    'repo': '/' + event['repo']['name']
                    }
                html = requests.get(event_data['url']).content
                soup = BS(html, 'lxml')
                event_data['content'] = soup.find(id='wiki-content')
                out.append(event_data)
            return out
        elif resp.status_code == 304:
            return []

class ES(object):
    github = GitEvents()
    def create_update_wiki_page(self, event):
        """
        given an event returned by GitEvents.get_events(), update the index
        """
        page_id = urllib.quote(urlparse(event['url']).path, '')
        url = '/'.join([settings.ES_HOST, 'wiki/page', page_id])
        return requests.put(url, data=event)
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
    def create_wiki_page(self, repo_name, url):
        """
        given an repo_name and a url, index the wiki page at the url
        """
        html = requests.get(url).content
        soup = BS(html, 'lxml')
        page_id = urllib.quote(urlparse(url).path, '')
        page_data = {
            'url': url,
            'title': soup.find(id='head').h1.text,
            'content': soup.find(id='wiki-content'),
            'repo': '/' + repo_name
        }
        url = '/'.join([settings.ES_HOST, 'wiki/page', page_id])
        return requests.put(url, data=page_data)
    def incremental_update_wiki(self):
        """
        update all wikis that have changed since last look
        """
        events = self.github.get_events()
        for event in events:
            self.update_wiki_page(event)
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
        print resp

es = ES()
es.index_new_repo('mbates/Design-DevRegroup')
#r = es.incremental_update_wiki()

