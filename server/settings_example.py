# the ElasticSearch host
ES_HOST = 'http://localhost:9200'

# the Jira host
JIRA_HOST = 'https://jira.example.com'

# the GitHub enterprise host
GITHUB = {
    'GHE': {
        'API': 'https://github.example.com',
        'WEB': 'https://github.example.com',
        'PAGES': 'https://github.example.com/pages/%s/%s/',
        'AUTH': (
            'user',
            'password',
        ),
    },
    'GH': {
        'API': 'https://api.github.com',
        'WEB': 'https://github.com',
        'ORGS': ['org_name'],
        'PAGES': 'https://%s/github.io/%s',
        'AUTH': (
            'user',
            'password',
        ),
    },   
}
