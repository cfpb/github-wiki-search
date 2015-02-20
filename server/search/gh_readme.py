from server.search import helpers
from server import settings
gh_settings = settings.GITHUB
from bs4 import SoupStrainer, BeautifulSoup as BS
from urlparse import urlparse
import urllib

from datetime import datetime
import time

obj_type = 'readme'

def index(gh_type, repo_name, gh_pool, force=False):
    start = time.mktime(datetime.now().timetuple())
    version = helpers.get_version_if_modified(gh_type, repo_name, obj_type, force)
    if not version:
        return
    bulk_data = index_readme(gh_type, repo_name, gh_pool)
    helpers.rebuild_repo_index(gh_type, repo_name, obj_type, bulk_data)
    helpers.save_indexed_version(gh_type, repo_name, obj_type, version)
    end = time.mktime(datetime.now().timetuple())
    print '%s: %s readmes (%s secs)' % (repo_name, len(bulk_data)/2, end-start)

def index_readme(gh_type, repo_name, gh_pool):
    url_template = '%s/%s/'
    url = url_template % (gh_settings[gh_type]['WEB'], repo_name)
    html = gh_pool.request('get', url).data
    strainer = SoupStrainer(id='readme')
    soup = BS(html, 'lxml', parse_only=strainer)
    path = urlparse(url).path  # remove initial slash
    page_id = urllib.quote(gh_type + path, '')

    h1 = soup.find('h1')
    if h1:
        title = ' '.join(h1.findAll(text=True)).strip()
    else:
        title = 'Readme'
    try:
        return ({
            "index": {
                "_index": "search", "_type": obj_type, "_id": page_id
        }},
        {
            'url': url,
            'title': title,
            'content': ' '.join(soup.find('article').findAll(text=True)).strip(),
            'path': '/' + repo_name,
            'source': {'GH': 'github', 'GHE': 'github enterprise'}[gh_type],
        },)
    except AttributeError:
        return []
