from server import settings
import helpers
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
        bulk_data += [{
            "index": {
                "_index": "search", "_type": "issue", "_id": issue['key']
            }},
            {
                'url': settings.JIRA_HOST + "/browse/" + issue['key'],
                'title': issue['fields']['summary'],
                'content': issue['fields']['description'],
                'author': (
                    issue['fields']['creator'].get('name', '')
                    if issue['fields'].get('creator')
                    else ''
                ),
                'updated_date': issue['fields']['updated'],
                'status': issue['fields']['status']['name'],
                'path': "/%s" % issue['fields']['project']['key'],
                'source': 'jira',
                'assignee': (issue['fields']['assignee'] or {}).get('name', None)
            }
        ]

        # use set type to prevent duplicates
        projs.add(issue['fields']['project']['key'])
        users.add(
            issue['fields']['creator'].get('name', '')
            if issue['fields'].get('creator')
            else ''
        )

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
                    'updated_date': comment['updated'],
                    'title': "Comment for Jira issue %s" % issue['key'],
                    'url': "%s/browse/%s?focusedCommentId=%s" % (settings.JIRA_HOST, issue['key'], comment['id']),
                    'status': None,
                    'path': "%s/%s" % (issue['fields']['project']['key'], issue['key']),
                    'source': 'jira',

            }]

            # use set() type to prevent duplicates
            if comment.get('author'):
                users.add(comment['author']['name'])

    # submit the issues to elasticsearch
    helpers.delete_index_subset('jira', 'issue')
    helpers.write_bulk_data(bulk_data)
    end = time.mktime(datetime.now().timetuple())
    print 'Jira: %s issues and comments (%s secs)' % (len(bulk_data)/2, end-start)
    return list(users), list(projs)
