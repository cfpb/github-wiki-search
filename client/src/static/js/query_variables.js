ac_test_data = {
    "took": 3,
    "timed_out": false,
    "_shards": {
        "total": 5,
        "successful": 5,
        "failed": 0
    },
    "hits": {
        "total": 2,
        "max_score": 1.0,
        "hits": [
            {
                "_index": "autocomplete",
                "_type": "user",
                "_id": "dgreisen",
                "_score": 1.0,
                "_source": {
                    "owner": "dgreisen",
                    "count": 2
                }
            },
            {
                "_index": "autocomplete",
                "_type": "repo",
                "_id": "dgreisen%2Fgithub-search",
                "_score": 1.0,
                "_source": {
                    "owner": "dgreisen",
                    "repo": "github-search",
                    "count": 2
                }
            }
        ]
    }
};
var searchResults = [];
var repoIdent = '/';
var ownerIdent = '@';

var currentRepoTerm = null;
var currentOwnerOwnly = null;

var queryLocation = '/search/search/_search';
var suggestRepoLocation = '/search/autocomplete/repo/_search';
var suggestOwnerLocation = '/search/autocomplete/user/_search';
var suggestionOwnerRepoLocation = '/search/autocomplete/_search';

var busy = false;
var query_from = 0;
var filteredQuery = {
    "filtered": {
        "filter": {
            "term": {
                "repo.path": "[/<owner>[/<repo>]]"
            }
        },
        "query": {
            "match": {
                "_all": "<query>"
            }
        }
    }
};


var queryData = {
    "fields": ["url", "path", "title", "assignee", "author"],
    "from": 0,
    "query": {},
    "highlight": {
        "pre_tags": ["<mark>"],
        "post_tags": ["</mark>"],
        "fields": {
            "content": {},
            "title": {
                "number_of_fragments": 0
            }
        }
    }
};

// when only looking for an owner
var suggestOwnerQuery = {
    "size": 5,
    "filter": {
        "term": {
            "owner": "<owner>"
        }
    }
};

// when looking for a specific owner/repo combination
var suggestRepoQuery = {
    "size": 5,
    "filter": {
        "bool": {
            "must": [
                {
                    "term": {
                        "owner": "<owner>"
                    }
                },
                {
                    "term": {
                        "repo": "<repo>"
                    }
                }
            ]
        }
    }
};
var allQuery = {
    "match": {
        "_all": "<query>"
    }
}


// when don't know whether the entered value is owner or repo
var suggestOwnerRepoQuery = {
    "size": 5,
    "filter": {
        "bool": {
            "should": [
                {
                    "term": {
                        "owner": "<owner>"
                    }
                },
                {
                    "term": {
                        "repo": "<repo>"
                    }
                }
            ]
        }
    }
};
