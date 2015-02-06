from jira import index as jira
from repos import index as repos
from gh_users import index as gh_users
from server.indexers import github_helpers as helpers
import time
from datetime import datetime

def index(gh_repos, ghe_repos, jira_users, jira_projs):
    start = time.mktime(datetime.now().timetuple())
    bulk_data = jira(jira_users, jira_projs)
    bulk_data += repos(gh_repos, ghe_repos)
    bulk_data += gh_users()
    helpers.reset_index('autocomplete')
    helpers.write_bulk_data(bulk_data)
    end = time.mktime(datetime.now().timetuple())
    print 'autocomplete: %s entries (%s secs)' % (len(bulk_data)/2, end-start)
