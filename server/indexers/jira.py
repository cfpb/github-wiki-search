from server import settings
import urllib3
import json
import github_helpers as helpers

from os import path
from universalclient import Client
es_client = Client(settings.ES_HOST)
DIR = path.dirname(path.realpath(__file__))

def index():
    """
    sync all jira issues
    """
    jira_endpoint = '%s/rest/api/2/search' % settings.JIRA_HOST
    jira_fields = 'fields=assignee,creator,created,project,status,summary,labels,description,comment'
    # TODO arbitrary date to keep queries small until this is more mature
    #jira_query = 'jql=updated>"2014/10/20"'
    jira_query = ''
    max_results = 500
    offset = 0
    jira_url = jira_endpoint + "?" + jira_fields + "&" + jira_query
    issues = []

    # Grab all data via API calls, 500 issues at a time
    while True:
        conn = urllib3.connection_from_url(settings.JIRA_HOST)
        json_result = conn.request('get', "%s&startAt=%d&maxResults=%d&" % (jira_url, offset, max_results)).data
        json_parsed = json.loads(json_result)
        issues += json_parsed['issues']
        if json_parsed["total"] > len(issues):
            offset += max_results
        else:
            break

    bulk_data_obj = []
    projs = set()
    users = set()

    # compile the proper data structure for elasticsearch
    for issue in issues:
        index = {}
        index['_type'] = "jira_issue"
        index['_id'] = issue['key']
        index['_index'] = 'search'
        obj = {}
        obj['url'] = settings.JIRA_HOST + "/browse/" + issue['key']
        obj['title'] = issue['fields']['summary']
        obj['content'] = issue['fields']['description']
        obj['author'] = issue['fields']['creator']['name']
        obj['created_date'] = issue['fields']['created']
        obj['status'] = issue['fields']['status']['name']
        obj['path'] = "%s" % issue['fields']['project']['key']
        if issue['fields']['assignee']:
            obj['assignee'] = issue['fields']['assignee']['name']
        else:
            obj['assignee'] = None
        bulk_data_obj.append({'index': index})
        bulk_data_obj.append(obj)

        # use set type to prevent duplicates
        projs.add(issue['fields']['project']['key'])
        users.add(obj['author'])
        if issue['fields']['assignee']:
            users.add(obj['assignee'])

        for comment in issue['fields']['comment']['comments']:
            comment_index = {}
            index['_type'] = "jira_issue"
            comment_index['_id'] = comment['id']
            index['_index'] = 'search'
            comment_obj = {}
            comment_obj['content'] = comment['body']
            if 'author' in comment.keys():
                comment_obj['author'] = comment['author']['name']
            else:
                comment_obj['author'] = None
            comment_obj['assignee'] = None
            comment_obj['created_date'] = comment['created']
            comment_obj['title'] = "Comment for Jira issue %s" % issue['key']
            comment_obj['url'] = "%s/browse/%s?focusedCommentId=%s" % (settings.JIRA_HOST, issue['key'], comment['id'])
            comment_obj['status'] = None
            comment_obj['path'] = "%s/%s" % (issue['fields']['project']['key'], issue['key'])

            bulk_data_obj.append({'index': comment_index})
            bulk_data_obj.append(comment_obj)

            # use set() type to prevent duplicates
            if comment_obj['author']:
                users.add(comment_obj['author'])
            if comment_obj['assignee']:
                users.add(comment_obj['assignee'])


    # submit the issues to elasticsearch
    helpers.delete_index_subset('jira', 'issue')
    helpers.write_bulk_data(bulk_data_obj)
    return list(users), list(projs)
