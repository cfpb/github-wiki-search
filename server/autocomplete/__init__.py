import jira
import repos
from server.indexers import github_helpers as helpers
import time
from datetime import datetime

def index(gh_repos, ghe_repos, jira_users, jira_projs):
    start = time.mktime(datetime.now().timetuple())
    bulk_data = jira.index(jira_users, jira_projs)
    bulk_data += repos.index(gh_repos, ghe_repos)
    # TODO: github users
    helpers.reset_index('autocomplete')
    helpers.write_bulk_data(bulk_data)
    end = time.mktime(datetime.now().timetuple())
    print 'autocomplete: %s entries (%s secs)' % (len(bulk_data)/2, end-start)
