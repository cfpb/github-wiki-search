import settings
ghe_settings = settings.GITHUB.get('GHE', {})
from universalclient import Client
import urllib3
import utils

from wiki import index as wiki
from readme import index as readme
from gh_pages import index as gh_pages
from gh_issues import index as gh_issues

ghe_api_client = Client(ghe_settings.get('API')).api.v3
ghe_pool = urllib3.connection_from_url(ghe_settings.get('WEB'), maxsize=50, block=True)

def _get_repos():
    if not ghe_settings:
        return []
    return [repo['full_name'] for repo in utils.iter_get(ghe_api_client.repositories) if not repo['fork']]


def index(pool, pages_pool, repo_names=None, force=False):
    repo_names = repo_names or _get_repos()
    jobs = [pool.spawn(wiki, 'GHE', repo_name, ghe_pool, force) for repo_name in repo_names]
    jobs += [pool.spawn(readme, 'GHE', repo_name, ghe_pool, force) for repo_name in repo_names]
    jobs = [pool.spawn(gh_pages, 'GHE', repo_name, pages_pool, force) for repo_name in repo_names]
    jobs = [pool.spawn(gh_issues, 'GHE', ghe_api_client, repo_name) for repo_name in repo_names]
    return jobs, repo_names
