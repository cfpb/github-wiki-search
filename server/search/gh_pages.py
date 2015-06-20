from server.search import helpers
from server import settings
gh_settings = settings.GITHUB
from bs4 import BeautifulSoup as BS
from urlparse import urlparse, urljoin
import urllib
import urllib3

import gevent
from gevent.pool import Pool
from datetime import datetime
import time
import re

index_regex = re.compile(r'index.html$')

obj_type = 'gh_page'

def index(gh_type, repo_name, gh_pool, force=False):
    start = time.mktime(datetime.now().timetuple())
    version = helpers.get_version_if_modified(gh_type, repo_name, obj_type, force)
    if not version:
        return
    bulk_data = index_gh_pages(gh_type, repo_name, gh_pool)
    helpers.rebuild_repo_index(gh_type, repo_name, obj_type, bulk_data)
    helpers.save_indexed_version(gh_type, repo_name, obj_type, version)
    end = time.mktime(datetime.now().timetuple())
    print '%s: %s gh_pages (%s secs)' % (repo_name, len(bulk_data)/2, end-start)


def index_gh_pages(gh_type, repo_name, gh_pool):
    """ return bulk rows for github pages for repo_name repo """
    url = gh_settings[gh_type]['PAGES'] % tuple(repo_name.split('/'))
    bulk_rows = index_gh_page(gh_type, gh_pool, url, repo_name, url, set([url]))
    return bulk_rows


def index_gh_page(gh_type, gh_pool, page_url, repo_name, base_url, already_visited):
    """
    return bulk rows for github page and all linked github pages
    that haven't already been visited
    """
    def gen_url(link):
        url = urljoin(page_url, link.get('href'))
        url = index_regex.sub('', url)
        url = url.split('#', 1)[0]
        return url

    def is_valid_url(url):
        # only index pages that have not already been indexed and that are in a gh_pages subfolder
        if not url or url in already_visited or not url.startswith(base_url):
            return False
        already_visited.add(url)
        return True
    # import pdb
    # pdb.set_trace()
    try:
        resp = gh_pool.request('get', page_url)
    except urllib3.exceptions.MaxRetryError:
        return []
    if resp.headers.get('content-type') != 'text/html' or resp.status >= 400:
        return []
    html = resp.data
    try:
        soup = BS(html, 'lxml')
    except:
        return []

    links = soup.find_all('a')
    child_urls = (gen_url(link) for link in links)
    child_urls = [url for url in child_urls if is_valid_url(url)]
    pool = Pool(20)
    jobs = [pool.spawn(index_gh_page, gh_type, gh_pool, child_url, repo_name, base_url, already_visited) for child_url in child_urls]
    gevent.joinall(jobs)
    helpers._rerase(jobs)

    bulk_rows = [row for job in jobs for row in job.value]
    page_id = urllib.quote(gh_type + urlparse(page_url).path, '')
    title = soup.find('title')
    title = title.text if title else page_url
    bulk_rows += [{
        "index": {
            "_index": "search", "_type": obj_type, "_id": page_id
        }},
        {
            'url': page_url,
            'title': title,
            'content': helpers.get_visible_text(soup),
            'path': '/' + repo_name,
            'source': gh_type,
    }]
    return bulk_rows
