from server.search import helpers
from server import settings
gh_settings = settings.GITHUB
from bs4 import SoupStrainer, BeautifulSoup as BS
from urlparse import urlparse
import urllib

import gevent
from gevent.pool import Pool
from datetime import datetime
import time

obj_type = 'wiki'

def index(gh_type, repo_name, gh_pool, force=False):
    start = time.mktime(datetime.now().timetuple())
    version = helpers.get_version_if_modified(gh_type, repo_name, obj_type, force)
    if not version:
        return
    bulk_data = index_wiki(gh_type, repo_name, gh_pool)
    helpers.rebuild_repo_index(gh_type, repo_name, obj_type, bulk_data)
    helpers.save_indexed_version(gh_type, repo_name, obj_type, version)
    end = time.mktime(datetime.now().timetuple())
    print '%s: %s wiki pages (%s secs)' % (repo_name, len(bulk_data)/2, end-start)

def index_wiki(gh_type, repo_name, gh_pool):
    """ return bulk rows for wiki for repo_name repo """
    # get and parse a list of all wiki page urls
    url_template = 'https://%s/%s/wiki/_pages'
    url = url_template % (gh_pool.host, repo_name)
    html = gh_pool.request('get', url).data
    strainer = SoupStrainer(id='wiki-content')
    soup = BS(html, 'lxml', parse_only=strainer)
    page_links = soup.find_all('a')
    page_urls = (('https://%s%s' % (gh_pool.host, link.get('href')))  for link in page_links)

    # index each page
    pool = Pool(20)
    jobs = [pool.spawn(index_wiki_page, gh_type, repo_name, page_url, gh_pool) for page_url in page_urls]
    gevent.joinall(jobs)
    helpers._rerase(jobs)
    bulk_data = [row for job in jobs for row in job.value]
    return bulk_data

def index_wiki_page(gh_type, repo_name, page_url, gh_pool):
    """ return bulk rows for wiki page at page_url for repo_name repo """
    html = gh_pool.request('get', page_url).data
    strainer = SoupStrainer(id='wiki-wrapper')
    soup = BS(html, 'lxml', parse_only=strainer)
    path = urlparse(page_url).path  # remove initial slash
    page_id = urllib.quote(gh_type + path, '')
    return ({
        "index": {
            "_index": "search", "_type": obj_type, "_id": page_id
    }},
    {
        'url': page_url,
        'title': ' '.join(soup.find(class_='gh-header-title').findAll(text=True)).strip(),
        'content': ' '.join(soup.find(id='wiki-body').findAll(text=True)).strip(),
        'path': '/' + repo_name,
        'source': {'GH': 'github', 'GHE': 'github enterprise'}[gh_type],
    },)
