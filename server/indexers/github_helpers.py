from universalclient import Client, jsonFilter
import urllib3
from server import settings
from gevent import subprocess
from server import schemas
import json
import bs4
import re

es_client = Client(settings.ES_HOST, dataFilter=jsonFilter)
es_pool = urllib3.connection_from_url(settings.ES_HOST,
                                      maxsize=50,
                                      block=True,
                                      headers=urllib3.util.make_headers(keep_alive=True)
                                     )

history_index = 'history'
search_index = 'search'

search_client = es_client.search
history_client = es_client.history


def save_indexed_version(gh_type, repo_name, typ, version):
    doc_id = (gh_type + '/' + repo_name).replace('/', '%2F')
    body = json.dumps({'version': version})

    url = '/%s/%s/%s/_update' % (history_index, typ, doc_id)
    resp = es_pool.urlopen('POST', url, body=body)
    if resp.status == 500:
        url = '/%s/%s/%s' % (history_index, typ, doc_id)
        resp = es_pool.urlopen('PUT', url, body=body)


def get_indexed_version(gh_type, repo_name, typ):
    doc_id = (gh_type + '/' + repo_name).replace('/', '%2F')

    url = '/%s/%s/%s' % (history_index, typ, doc_id)
    resp = es_pool.request('GET', url)
    version = json.loads(resp.data).get('_source', {}).get('version')
    return version


def get_latest_version(gh_type, repo_name, typ):
    commands = {
        'wiki': 'git ls-remote %s/%s.wiki.git HEAD' % (settings.GITHUB[gh_type]['WEB'], repo_name),
        'gh_page': 'git ls-remote %s/%s.git -b gh-pages' % (settings.GITHUB[gh_type]['WEB'], repo_name),
        'readme': 'git ls-remote %s/%s.git HEAD' % (settings.GITHUB[gh_type]['WEB'], repo_name),
    }
    sp = subprocess.Popen(commands[typ].split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    version = sp.stdout.read().split('\t')[0]
    return version


def get_version_if_modified(gh_type, repo_name, typ, force=False):
    """
    Return the latest version if the latest version is different
    from the previously indexed version.
    Return None if no change.
    if force in True, always return the latest version
    """
    latest_version = get_latest_version(gh_type, repo_name, typ)
    if force:
        return latest_version
    indexed_version = get_indexed_version(gh_type, repo_name, typ)

    if indexed_version == latest_version:
        print '%s (%s): skipping %s' % (repo_name, gh_type, typ)
        return None
    else:
        return latest_version


def delete_index_subset(source, typ, repo_name=None):
    source = {'GH': 'github', 'GHE': 'github enterprise'}.get(source, source)
    # TODO: this isn't working
    query = {"query": {
      "filtered": {
        "filter": {
          "and": [
            {
              "term": {
                "source": source
              },
            },
          ],
        },
      },
    }}
    if repo_name:
        query['query']['filtered']['filter']['and'].append({
          "term": {
            "path.path_full": repo_name
          },
        })

    url = '/%s/%s/_query' % (search_index, typ)
    body = json.dumps(query)
    es_pool.urlopen('DELETE', url, body=body)


def rebuild_repo_index(gh_type, repo_name, typ, bulk_data):
    delete_index_subset(gh_type, typ, repo_name)
    write_bulk_data(bulk_data)

def create_index(db_name):
    schema = getattr(schemas, db_name, {})
    url = '/%s' % db_name
    body = json.dumps(schema)
    es_pool.urlopen('POST', url, body=body)

def reset_index(db_name):
    url = '/%s' % db_name
    es_pool.request('DELETE', url)
    create_index(db_name)

def _rerase(jobs):
    if any([job.exception for job in jobs]):
        raise BaseException('sub-gevent error')

def write_bulk_data(bulk_data):
    if not bulk_data:
        return
    bulk_rows = '\n'.join([json.dumps(row) for row in bulk_data]) + '\n'
    es_pool.urlopen('POST', '/_bulk', body=bulk_rows)
    es_pool.request('POST', '/_refresh')


return_regex = re.compile(r'\W*\n\W*')
def get_visible_text(soup):
    texts = soup.findAll(text=True)

    def visible(element):
        if element.parent.name in ['style', 'script', '[document]', 'head', 'title']:
            return False
        elif isinstance(element, bs4.element.Comment):
            return False
        return True

    out = ' '.join(filter(visible, texts))
    out = return_regex.sub('\n ', out)
    return out
