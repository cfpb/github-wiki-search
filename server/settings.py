import os


# Elasticsearch host
ES_HOST = os.getenv("ES_HOST")

# JIRA host
JIRA_HOST = os.getenv("JIRA_HOST")

# GitHub Enterprise
GHE_HOST = os.getenv("GHE_HOST")
GHE_USER = os.getenv("GHE_USER")
GHE_AUTH_TOKEN = os.getenv("GHE_AUTH_TOKEN")

# Public GitHub
GH_ORG = os.getenv("GH_ORG")
GH_USER = os.getenv("GH_USER")
GH_AUTH_TOKEN = os.getenv("GH_AUTH_TOKEN")

# GitHub (and GitHub Enterprise) configs
GITHUB = {
    "GHE": {
        "API": GHE_HOST,
        "API_PATH": "/api/v3",
        "WEB": GHE_HOST,
        "PAGES": "{}/pages/%s/%s/".format(GHE_HOST),
        "AUTH": (GHE_USER, GHE_AUTH_TOKEN),
    },
    "GH": {
        "API": "https://api.github.com",
        "WEB": "https://github.com",
        "ORGS": [GH_ORG],
        "PAGES": "https://%s/github.io/%s",
        "AUTH": (GH_USER, GH_AUTH_TOKEN),
    },
}
