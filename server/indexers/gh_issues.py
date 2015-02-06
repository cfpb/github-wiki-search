from server.indexers import github_helpers as helpers
from server.utils import iter_get

from datetime import datetime, timedelta
from urlparse import urlparse
import time

obj_type = 'issue'


def index(gh_type, client, repo_name):
    start = time.mktime(datetime.now().timetuple())
    indexed_timestamp = helpers.get_indexed_version(gh_type, repo_name, obj_type)
    # increment timestamp by one second to prevent duplicates
    indexed_timestamp = nudge_datetime(indexed_timestamp)
    bulk_data = index_gh_issues(gh_type, client, repo_name, indexed_timestamp)
    bulk_data += index_gh_issue_comments(gh_type, client, repo_name, indexed_timestamp)
    helpers.update_repo_index(gh_type, repo_name, obj_type, bulk_data)
    end = time.mktime(datetime.now().timetuple())
    print '%s: %s github issues (%s secs)' % (repo_name, len(bulk_data)/2, end-start)


def index_gh_issues(gh_type, client, repo_name, since):
    (owner, repo) = repo_name.split('/')
    issues = iter_get(client.repos._(owner)._(repo).issues.params(
        state='all', since=since))

    bulk_data = []
    most_recent_timestamp = ""
    for issue in issues:
        index = {}
        index["_index"] = "search"
        index["_type"] = obj_type
        index["_id"] = "%s/%s" % (repo_name, issue['number'])
        obj = {}
        obj['url'] = issue['html_url']
        obj['title'] = issue['title']
        obj['content'] = issue['body']
        obj['author'] = issue['user']['login']
        obj['updated_date'] = issue['updated_at']
        obj['status'] = issue['state']
        if issue['assignee']:
            obj['assignee'] = issue['assignee']['login']
        obj['path'] = '/' + repo_name
        obj['loc'] = {'GH': 'github', 'GHE': 'github enterprise'}[gh_type]

        bulk_data.append({'index': index})
        bulk_data.append(obj)

        if most_recent_timestamp < issue['updated_at']:
            most_recent_timestamp = issue['updated_at']

    # Update the 'latest version'
    if most_recent_timestamp:
        helpers.save_indexed_version(gh_type, repo_name, obj_type,
                                     most_recent_timestamp)

    return bulk_data


def index_gh_issue_comments(gh_type, client, repo_name, since):
    (owner, repo) = repo_name.split('/')
    comments = iter_get(client.repos._(owner)._(repo).issues.comments.params(since=since))

    bulk_data = []
    for comment in comments:
        # parse issue number from url
        # example: https://api.github.com/myorg/myname/myrepo/issues/1
        issue_id = urlparse(comment['issue_url']).path.split('/')[-1]

        index = {}
        index["_index"] = "search"
        index["_type"] = obj_type
        index["_id"] = "%s/%s/%s" % (repo_name, issue_id, comment['id'])
        obj = {}
        obj['url'] = comment['html_url']
        obj['title'] = 'Comment for %s issue %s' % (repo_name, issue_id)
        obj['content'] = comment['body']
        obj['author'] = comment['user']['login']
        obj['updated_date'] = comment['updated_at']
        obj['path'] = '/%s/%s' % (repo_name, issue_id)
        obj['loc'] = {'GH': 'github', 'GHE': 'github enterprise'}[gh_type]

        bulk_data.append({'index': index})
        bulk_data.append(obj)

    return bulk_data


# Move time ahead one second
def nudge_datetime(timestamp):
    if timestamp:
        datetime_obj = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        datetime_obj = datetime_obj + timedelta(seconds=1)
        return datetime_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
