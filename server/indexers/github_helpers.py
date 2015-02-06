from universalclient import Client, jsonFilter
from server import settings
import subprocess
from server import schemas
import json
import bs4
import re

es_client = Client(settings.ES_HOST, dataFilter=jsonFilter)
search_client = es_client.search
ac_client = es_client.autocomplete
history_client = es_client.history


def save_indexed_version(gh_type, repo_name, typ, version):
    doc_id = (gh_type + '/' + repo_name).replace('/', '%2F')
    # TODO: create; update if error
    resp = history_client._(typ)._(doc_id)._update.post(data={'version': version})
    if resp.status_code == 500:
        history_client._(typ)._(doc_id).put(data={'version': version})


def get_indexed_version(gh_type, repo_name, typ):
    doc_id = (gh_type + '/' + repo_name).replace('/', '%2F')
    resp = history_client._(typ)._(doc_id).get()
    version = resp.json().get('_source', {}).get('version')
    return version


def get_latest_version(gh_type, repo_name, typ):
    commands = {
        'wiki': 'git ls-remote %s/%s.wiki.git HEAD' % (settings.GITHUB[gh_type]['WEB'], repo_name),
        'pages': 'git ls-remote %s/%s.git -b gh-pages' % (settings.GITHUB[gh_type]['WEB'], repo_name),
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


def delete_index_subset(loc, typ, repo_name=None):
    loc = {'GH': 'github', 'GHE': 'github enterprise'}.get(loc, loc)
    # TODO: this isn't working
    query = {"query": {
      "filtered": {
        "filter": {
          "and": [
            {
              "term": {
                "loc": loc
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
    search_client._(typ)._query.delete(data=query)


def update_repo_index(gh_type, repo_name, typ, bulk_data):
    delete_index_subset(gh_type, typ, repo_name)
    write_bulk_data(bulk_data)

def create_index(db_name):
    schema = getattr(schemas, db_name, {})
    es_client._(db_name).post(data=schema)

def reset_index(db_name):
    es_client._(db_name).delete()
    create_index(db_name)

def _rerase(jobs):
    if any([job.exception for job in jobs]):
        raise BaseException('sub-gevent error')

def write_bulk_data(bulk_data):
    if not bulk_data:
        return
    bulk_rows = '\n'.join([json.dumps(row) for row in bulk_data]) + '\n'
    es_client._bulk.dataFilter().post(data=bulk_rows)
    es_client._refresh.post()


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
