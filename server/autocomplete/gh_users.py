from server import utils, search
import itertools

gh_settings = search.gh.gh_settings
ghe_settings = search.ghe.ghe_settings

gh_api_client = search.gh.gh_api_client
ghe_api_client = search.ghe.ghe_api_client

def _get_org_users(org_name):
    return (user for user in utils.iter_get(gh_api_client.orgs._(org_name).members))

def get():
    user_iters = []
    if gh_settings.get('ORGS'):
        user_iters = [_get_org_users(org_name) for org_name in gh_settings['ORGS']]
    if ghe_settings:
        user_iters.append(utils.iter_get(ghe_api_client.users))
    return set((user['login'] for user in itertools.chain(*user_iters)))
