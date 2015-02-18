from server.search import helpers
from server.utils import iter_get_url
from server import settings
import json
from datetime import datetime, timedelta
from urlparse import urlparse
import time
import urllib

obj_type = 'issue'


def index(gh_type, pool, repo_name):
    start = time.mktime(datetime.now().timetuple())
    indexed_timestamp = helpers.get_indexed_version(gh_type, repo_name, obj_type)
    # increment timestamp by one second to prevent duplicates
    indexed_timestamp = nudge_datetime(indexed_timestamp)
    bulk_data = []
    if is_updated_issues(gh_type, pool, repo_name, indexed_timestamp):
        bulk_data, most_recent_timestamp = index_gh_issues(gh_type, pool, repo_name)
        bulk_data += index_gh_issue_comments(gh_type, pool, repo_name)
        helpers.rebuild_repo_index(gh_type, repo_name, obj_type, bulk_data)
        # Update the 'latest version'
        if most_recent_timestamp:
            helpers.save_indexed_version(gh_type, repo_name, obj_type,
                                         most_recent_timestamp)

    end = time.mktime(datetime.now().timetuple())
    print '%s: %s github issues/comments (%s secs)' % (repo_name, len(bulk_data)/2, end-start)


def is_updated_issues(gh_type, pool, repo_name, since):
    fields = {'state': 'all'}
    if since:
        fields = {'state': 'all', 'since': since}
    url = settings.GITHUB[gh_type].get('API_PATH', '')
    url += '/repos/%s/issues?%s' % (repo_name, urllib.urlencode(fields))
    resp = pool.request('GET', url)
    issues = json.loads(resp.data)
    return True if issues else False


def index_gh_issues(gh_type, pool, repo_name, since=None):
    fields = {'state': 'all'}
    if since:
        fields['since'] = since
    url = settings.GITHUB[gh_type].get('API_PATH', '')
    url += '/repos/%s/issues?%s' % (repo_name, urllib.urlencode(fields))
    issues = iter_get_url(url, pool)

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
        obj['source'] = {'GH': 'github', 'GHE': 'github enterprise'}[gh_type]

        bulk_data.append({'index': index})
        bulk_data.append(obj)

        if most_recent_timestamp < issue['updated_at']:
            most_recent_timestamp = issue['updated_at']

    return bulk_data, most_recent_timestamp


def index_gh_issue_comments(gh_type, pool, repo_name, since=None):
    fields = {}
    if since:
        fields = {'since': since}
    url = settings.GITHUB[gh_type].get('API_PATH', '')
    url += '/repos/%s/issues/comments?%s' % (repo_name, urllib.urlencode(fields))
    comments = iter_get_url(url, pool)

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
        obj['source'] = {'GH': 'github', 'GHE': 'github enterprise'}[gh_type]

        bulk_data.append({'index': index})
        bulk_data.append(obj)

    return bulk_data


# Move time ahead one second
def nudge_datetime(timestamp):
    if timestamp:
        datetime_obj = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        datetime_obj = datetime_obj + timedelta(seconds=1)
        return datetime_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
