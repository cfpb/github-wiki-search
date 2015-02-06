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

    bulk_data = []
    projs = set()
    users = set()

    # compile the proper data structure for elasticsearch
    for issue in issues:
        bulk_data += [{
            "index": {
                "_index": "search", "_type": "issue", "_id": issue['key']
            }},
            {
                'url': settings.JIRA_HOST + "/browse/" + issue['key'],
                'title': issue['fields']['summary'],
                'content': issue['fields']['description'],
                'author': issue['fields']['creator']['name'],
                'created_date': issue['fields']['created'],
                'status': issue['fields']['status']['name'],
                'path': "%s" % issue['fields']['project']['key'],
                'loc': 'jira',
                'assignee': (issue['fields']['assignee'] or {}).get('name', None)
            }
        ]

        # use set type to prevent duplicates
        projs.add(issue['fields']['project']['key'])
        users.add(issue['fields']['creator']['name'])
        if issue['fields']['assignee']:
            users.add(issue['fields']['assignee']['name'])

        for comment in issue['fields']['comment']['comments']:
            bulk_data += [{
                "index": {
                    "_index": "search", "_type": "issue", "_id": comment['id']
                }},
                {
                    'author': (comment.get('author') or {}).get('name', None),
                    'content': comment['body'],
                    'assignee': None,
                    'created_date': comment['created'],
                    'title': "Comment for Jira issue %s" % issue['key'],
                    'url': "%s/browse/%s?focusedCommentId=%s" % (settings.JIRA_HOST, issue['key'], comment['id']),
                    'status': None,
                    'path': "%s/%s" % (issue['fields']['project']['key'], issue['key']),
                    'loc': 'jira',

            }]

            # use set() type to prevent duplicates
            if comment.get('author'):
                users.add(comment['author']['name'])


    # submit the issues to elasticsearch
    helpers.delete_index_subset('jira', 'issue')
    helpers.write_bulk_data(bulk_data)
    return list(users), list(projs)
