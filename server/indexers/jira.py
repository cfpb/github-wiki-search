import settings
import github_helpers as helpers

from universalclient import Client
import time
from datetime import datetime

jira_api_client = Client(settings.JIRA_HOST).rest.api._(2)
jira_fields = 'assignee,creator,updated,project,status,summary,labels,description,comment'
max_results = 500


def index():
    """
    sync all jira issues
    """
    offset = 0
    issues = []

    start = time.mktime(datetime.now().timetuple())

    # Grab all data via API calls, 500 issues at a time
    # TODO gevent solution
    while True:
        resp = jira_api_client.search.params(fields=jira_fields,
                                             startAt=offset,
                                             maxResults=max_results,
                                             ).get().json()
        issues += resp['issues']
        if resp['total'] > len(issues):
            offset += max_results
        else:
            break

    bulk_data = []
    projs = set()
    users = set()

    # compile the proper data structure for elasticsearch
    for issue in issues:
        index = {}
        index['_type'] = "issue"
        index['_id'] = issue['key']
        index['_index'] = 'search'
        obj = {}
        obj['url'] = settings.JIRA_HOST + "/browse/" + issue['key']
        obj['title'] = issue['fields']['summary']
        obj['content'] = issue['fields']['description']
        obj['author'] = issue['fields']['creator']['name']
        obj['updated_date'] = issue['fields']['updated']
        obj['status'] = issue['fields']['status']['name']
        obj['path'] = "%s" % issue['fields']['project']['key']
        obj['loc'] = 'jira'
        if issue['fields']['assignee']:
            obj['assignee'] = issue['fields']['assignee']['name']
        else:
            obj['assignee'] = None
        bulk_data.append({'index': index})
        bulk_data.append(obj)

        # use set type to prevent duplicates
        projs.add(issue['fields']['project']['key'])
        users.add(obj['author'])
        if issue['fields']['assignee']:
            users.add(obj['assignee'])

        for comment in issue['fields']['comment']['comments']:
            comment_index = {}
            index['_type'] = "comment"
            comment_index['_id'] = comment['id']
            index['_index'] = 'search'
            comment_obj = {}
            comment_obj['content'] = comment['body']
            if 'author' in comment.keys():
                comment_obj['author'] = comment['author']['name']
            else:
                comment_obj['author'] = None
            comment_obj['assignee'] = None
            comment_obj['updated_date'] = comment['updated']
            comment_obj['title'] = "Comment for Jira issue %s" % issue['key']
            comment_obj['url'] = "%s/browse/%s?focusedCommentId=%s" % (settings.JIRA_HOST, issue['key'], comment['id'])
            comment_obj['status'] = None
            comment_obj['path'] = "%s/%s" % (issue['fields']['project']['key'], issue['key'])
            comment_obj['loc'] = 'jira'

            bulk_data.append({'index': comment_index})
            bulk_data.append(comment_obj)

            # use set() type to prevent duplicates
            if comment_obj['author']:
                users.add(comment_obj['author'])
            if comment_obj['assignee']:
                users.add(comment_obj['assignee'])

    # submit the issues to elasticsearch
    helpers.delete_index_subset('jira', 'issue')
    helpers.write_bulk_data(bulk_data)
    end = time.mktime(datetime.now().timetuple())
    print 'Jira: %s issues and comments (%s secs)' % (len(bulk_data)/2, end-start)
    return list(users), list(projs)
