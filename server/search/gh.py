from server import settings
gh_settings = settings.GITHUB.get('GH', {})
from universalclient import Client
import urllib3
from server import utils
import itertools

from gh_wiki import index as gh_wiki
from gh_readme import index as gh_readme
from gh_pages import index as gh_pages
from gh_issues import index as gh_issues

headers = {
    'keep_alive': True,
    'user_agent': 'cfpb-tiresias',
}

gh_api_client = Client(gh_settings.get('API'))

if 'AUTH' in gh_settings:
    gh_api_client = gh_api_client.auth(gh_settings['AUTH'])
    headers['basic_auth'] = '%s:%s' % gh_settings['AUTH']

gh_pool = urllib3.connection_from_url(gh_settings.get('WEB'), maxsize=50, block=True)
gh_api_pool = urllib3.connection_from_url(gh_settings.get('API'), maxsize=50, block=True, headers=urllib3.util.make_headers(**headers))

def _get_org_repos(org_name):
    return (repo['full_name'] for repo in utils.iter_get_url('/orgs/%s/repos' % org_name, gh_api_pool) if not repo['fork'])

def get_repos():
    if not gh_settings.get('ORGS'):
        return []
    org_iters = [_get_org_repos(org_name) for org_name in gh_settings['ORGS']]
    return [repo_name for repo_name in itertools.chain(*org_iters)]


def index(pool, pages_pool, repo_names=None, force=False):
    repo_names = get_repos() if repo_names is None else repo_names
    jobs = [pool.spawn(gh_wiki, 'GH', repo_name, gh_pool, force) for repo_name in repo_names]
    jobs += [pool.spawn(gh_readme, 'GH', repo_name, gh_pool, force) for repo_name in repo_names]
    jobs += [pool.spawn(gh_pages, 'GH', repo_name, pages_pool, force) for repo_name in repo_names]
    jobs = [pool.spawn(gh_issues, 'GH', gh_api_pool, repo_name) for repo_name in repo_names]
    return jobs, repo_names
