import gh_paths
import gh_users
from server.search import helpers
import time
from datetime import datetime

def generate_bulk_data(users, paths):
    bulk_data = []
    for user in users:
        bulk_data.append({
            "index": {
                "_index": "autocomplete", "_type": "user", "_id": user,
        }})
        bulk_data.append({
            'user': user,
        })

    for path in paths:
        bulk_data.append({
            "index": {
                "_index": "autocomplete", "_type": "path", "_id": path,
        }})
        bulk_data.append({
            'path': path,
        })
    return bulk_data

def index(gh_repos, ghe_repos, jira_users, jira_projs):
    start = time.mktime(datetime.now().timetuple())

    users = set(jira_users).union(gh_users.get())
    paths = set(jira_projs).union(gh_paths.get(gh_repos, ghe_repos))

    bulk_data = generate_bulk_data(users, paths)

    helpers.reset_index('autocomplete')
    helpers.write_bulk_data(bulk_data)
    end = time.mktime(datetime.now().timetuple())
    print 'autocomplete: %s entries (%s secs)' % (len(bulk_data)/2, end-start)
