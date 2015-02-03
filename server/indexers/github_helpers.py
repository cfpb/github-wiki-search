from universalclient import Client, jsonFilter
from server import settings
import subprocess
from server import schemas

es_client = Client(settings.ES_HOST, dataFilter=jsonFilter)
search_client = es_client.search
ac_client = es_client.autocomplete
history_client = es_client.history

def get_latest_version(repo_name, typ):
    commands = {
        'wiki': 'git ls-remote %s/%s.wiki.git HEAD' % (settings.GITHUB_HOST, repo_name),
        'pages': 'git ls-remote %s/%s.git -b gh-pages' % (settings.GITHUB_HOST, repo_name),
        'readme': 'git ls-remote %s/%s.git HEAD' % (settings.GITHUB_HOST, repo_name),
    }
    sp = subprocess.Popen(commands[typ].split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    version = sp.stdout.read().split('\t')[0]
    return version


def get_indexed_version(repo_name, typ):
    escaped_repo_name = repo_name.replace('/', '%2F')
    resp = history_client._(typ)._(escaped_repo_name).get()
    version = resp.json().get('_source', {}).get('version')
    return version


def get_version_if_modified(repo_name, typ):
    """
    Return the latest version if the latest version is different
    from the previously indexed version.
    Return None if no change.
    """
    latest_version = get_latest_version(repo_name, typ)
    indexed_version = get_indexed_version(repo_name, typ)

    if indexed_version == latest_version:
        return None
    else:
        return latest_version


def save_indexed_version(repo_name, typ, version):
    repo_name = repo_name.replace('/', '%2F')
    # TODO: create; update if error
    resp = history_client._(typ)._(repo_name)._update.post(data={'version': version})
    if resp.status_code == 500:
        history_client._(typ)._(repo_name).put(data={'version': version})

def delete_repo_type(repo_name, typ):
    query = {"query": {
      "filtered": {
        "filter": {
          "term": {
            "path.path_full": repo_name
          }
        }
      }
    }}
    search_client._(typ)._query.delete(data=query)


def update_repo_index(repo_name, typ, bulk_data):
    delete_repo_type(repo_name, typ)
    es_client._bulk.post(data=bulk_data)


def reset_index(db_name):
    schema = getattr(schemas, db_name, {})
    es_client._(db_name).delete()
    es_client._(db_name).post(data=schema)


def _rerase(jobs):
    if any([job.exception for job in jobs]):
        raise BaseException('sub-gevent error')

