import gevent
import gh
import ghe
import jira
import urllib3
from gevent import monkey
from gevent.pool import Pool

# patches stdlib (including socket and ssl modules) to cooperate with other greenlets
monkey.patch_all()

def make_pools():
    pool = Pool(50)
    pages_pool = urllib3.PoolManager(20)
    return pool, pages_pool


def index():
    pool, pages_pool = make_pools()
    gh_jobs, gh_repos = gh.index(pool, pages_pool)
    ghe_jobs, ghe_repos = ghe.index(pool, pages_pool)
    gevent.joinall(gh_jobs + ghe_jobs)
    jira_users, jira_projs = jira.index()
    return gh_repos, ghe_repos, jira_users, jira_projs
