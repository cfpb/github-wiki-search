from server.indexers import github_helpers as helpers
from server import settings
from bs4 import SoupStrainer, BeautifulSoup as BS
import urllib3
import gevent
from gevent import monkey
from gevent.pool import Pool
from urlparse import urlparse
import urllib

pool = Pool(50)

# patches stdlib (including socket and ssl modules) to cooperate with other greenlets
monkey.patch_all()

def index(repo):
    version = helpers.get_modified_version(repo['full_name'], 'wiki')
    if not version:
        return

def index_wiki(repo_name):
    """ return bulk rows for wiki for repo_name repo """
    # get and parse a list of all wiki page urls
    url_template = '%s/%s/wiki/_pages'
    url = url_template % (settings.GITHUB_HOST, repo_name)
    html = urllib3.request('get', url).data
    strainer = SoupStrainer(class_='markdown-body')
    soup = BS(html, 'lxml', parse_only=strainer)
    if not soup.ul:
        return []
    page_links = soup.ul.find_all('a')
    page_urls = (settings.GITHUB_HOST + link.get('href') for link in page_links)

    # index each page
    jobs = [pool.spawn(index_wiki_page, repo_name, page_url) for page_url in page_urls]
    gevent.joinall(jobs)
    helpers._rerase(jobs)
    bulk_rows = [row for job in jobs for row in job.value]
    _write_bulk_rows(repo_name, 'wiki', bulk_rows)

def index_wiki_page(repo_name, page_url):
    """ return bulk rows for wiki page at page_url for repo_name repo """
    html = urllib3.request('get', page_url).read()
    strainer = SoupStrainer(id='wiki-wrapper')
    soup = BS(html, 'lxml', parse_only=strainer)
    path = urlparse(page_url).path[1:]
    page_id = urllib.quote(path, '')  # remove initial slash
    return ({ 
        "index": {
            "_index": "docs", "_type": "wiki_page", "_id": page_id
    }},
    {
        'url': page_url,
        'title': ' '.join(soup.find(id='head').h1.findAll(text=True)),
        'content': ' '.join(soup.find(id='wiki-content').findAll(text=True)),
        'repo': '/' + repo_name
    },)


