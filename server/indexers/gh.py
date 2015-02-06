import settings
from universalclient import Client
import urllib3
import utils
import itertools

from wiki import index as wiki
from readme import index as readme
from gh_pages import index as gh_pages
from gh_issues import index as gh_issues

gh_pool = urllib3.connection_from_url(settings.GITHUB.get('GH', {}).get('WEB'), maxsize=50, block=True)
gh_api_client = Client(settings.GITHUB.get('GH', {}).get('API'))

def _get_gh_org_repos(org_name):
    if not settings.GITHUB.get('GHE', {}).get('API'):
        return []
    return (repo['full_name'] for repo in utils.iter_get(gh_api_client.orgs._(org_name).repos) if not repo['fork'])

def _get_gh_repos():
    if not settings.GITHUB.get('GH', {}).get('ORGS'):
        return []
    org_iters = [_get_gh_org_repos(org_name) for org_name in settings.GITHUB['GH']['ORGS']]
    return [repo_name for repo_name in itertools.chain(*org_iters)]


def index(pool, pages_pool, repo_names=None, force=False):
    repo_names = repo_names or _get_gh_repos()
    jobs = [pool.spawn(wiki, 'GH', repo_name, gh_pool, force) for repo_name in repo_names]
    jobs += [pool.spawn(readme, 'GH', repo_name, gh_pool, force) for repo_name in repo_names]
    jobs += [pool.spawn(gh_pages, 'GH', repo_name, pages_pool, force) for repo_name in repo_names]
    jobs = [pool.spawn(gh_issues, 'GH', gh_api_client, repo_name) for repo_name in repo_names]
    return jobs, repo_names
