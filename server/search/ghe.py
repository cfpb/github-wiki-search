from server import settings
ghe_settings = settings.GITHUB.get('GHE', {})
from universalclient import Client
import urllib3
from server import utils

from gh_wiki import index as gh_wiki
from gh_readme import index as gh_readme
from gh_pages import index as gh_pages
from gh_issues import index as gh_issues

ghe_api_client = Client(ghe_settings.get('API')).api.v3

ghe_api_pool = urllib3.connection_from_url(ghe_settings.get('API'),
                                           maxsize=50,
                                           block=True,
                                           headers=urllib3.util.make_headers(keep_alive=True)
                                          )
ghe_pool = urllib3.connection_from_url(ghe_settings.get('WEB'), maxsize=50, block=True)

def get_repos():
    if not ghe_settings:
        return []
    return [repo['full_name'] for repo in utils.iter_get_url(ghe_settings['API_PATH'] + '/repositories', ghe_api_pool) if not repo['fork']]


def index(pool, pages_pool, repo_names=None, force=False):
    repo_names = get_repos() if repo_names is None else repo_names
    jobs = [pool.spawn(gh_wiki, 'GHE', repo_name, ghe_pool, force) for repo_name in repo_names]
    jobs += [pool.spawn(gh_readme, 'GHE', repo_name, ghe_pool, force) for repo_name in repo_names]
    jobs = [pool.spawn(gh_pages, 'GHE', repo_name, pages_pool, force) for repo_name in repo_names]
    jobs = [pool.spawn(gh_issues, 'GHE', ghe_api_pool, repo_name) for repo_name in repo_names]
    return jobs, repo_names
