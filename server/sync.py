#! /usr/bin/python
from universalclient import Client
import bs4
from bs4 import SoupStrainer, BeautifulSoup as BS
import settings
from urlparse import urlparse, urljoin
import urllib
import json
from datetime import datetime
import gevent
from gevent import monkey
from gevent.pool import Pool
import itertools
import os
from gevent import subprocess

pool = Pool(50)

# patches stdlib (including socket and ssl modules) to cooperate with other greenlets
monkey.patch_all()

import urllib3
from os import path
from os.path import join as path_join

DIR = path.dirname(path.realpath(__file__))
LOG = path_join(DIR, '..', 'client', 'dist', 'log')
CACHE = path.join(DIR, 'cache')

es_client = Client(settings.ES_HOST)
gh_client = Client(settings.GITHUB_HOST)
gh_api_client = gh_client.api.v3

def index_all_repos():
    """
    index all repos, reset elasticsearch, rebuild elasticsearchindices
    """
    start_time = datetime.now()
    repo_names = (repo['full_name'] for page in _get_paginated_repos() for repo in page)
    indexing = {'tot': 0, 'cur':set(), 'skipped': 0}
    jobs = [pool.spawn(index_repo, repo_name, indexing) for repo_name in repo_names]
    gevent.joinall(jobs)

    # _rebuild_indices()
    # repo_data = [job.value for job in jobs]
    # bulk_rows = (row for item in repo_data for row in item['bulk_rows'])
    # bulk_rows = itertools.chain(bulk_rows, index_all_users(repo_data))
    # bulk_data = '\n'.join([json.dumps(row) for row in bulk_rows]) + '\n'

    # print "writing bulk data"
    # with open(path_join(DIR, 'bulk_data.txt'), 'w') as f:
    #     f.write(bulk_data)

    # # reset index
    # es_client.docs.delete()
    # es_client.autocomplete.delete()
    # with open(path_join(DIR, 'schema', 'docs.json'), 'r') as schema_page:
    #     es_client.docs.post(data=schema_page.read())
    # with open(path_join(DIR, 'schema', 'autocomplete.json'), 'r') as schema_auto:
    #     es_client.autocomplete.post(data=schema_auto.read())
    # resp = es_client._bulk.post(data=bulk_data)
    # es_client._refresh.post()
    print 'total time:', datetime.now() - start_time
#    return resp

# def _rebuild_indices():
#     user_names = os.listdir(CACHE)
#     state = {'reset': False, bulk_rows: []}
#     jobs = [pool.spawn(_collect_user_rows, user_name, state) for user_name in user_names]
#     gevent.joinall(jobs)

# def _collect_user_rows(user_name, state):
#     repo_names = os.listdir(path_join(CACHE, user_name))
#     jobs = [pool.spawn(_collect_repo_rows, user_name, repo_name) for repo_name in repo_names]
#     gevent.joinall(jobs)
# #    repo_rows =

# def _collect_repo_rows(user_name, repo_name):
#     repo_dir = path_join(CACHE, user_name, repo_name)
#     file_names = os.listdir()
#     file_names.remove('meta')
#     files =
#     bulk_row_docs.remove('')


def _get_jira_issue_url(issue_id):
    return settings.JIRA_HOST + "/browse/" + issue_id

def _get_jira_issue_soup(issue_id, element_id):
    """
    return generator that given an issue id, gets the content, parses it and
    returns a tuple of the issue id and a soup of the tag with the given id
    """
    html = urllib2.urlopen(_get_jira_issue_url(issue_id)).read()
    strainer = SoupStrainer(id=element_id)
    soup = BS(html, parse_only=strainer)
    return (issue_id, soup)

def _get_paginated_repos():
    """
    generate paginated list of all repos in the enterprise github system
    """
    last_repo_id = 0
    while last_repo_id is not None:
        print last_repo_id
        params={"since": last_repo_id}
        repos = gh_api_client.repositories.get(params=params).json()
        last_repo_id = repos[-1]['id'] if repos else None
        if last_repo_id:
            yield repos

def index_repo(repo_name, indexing):
    """
    return a dict of {'user', 'page_count', 'bulk_rows'}
    for the given repo_name
    """
    user, repo = repo_name.split('/')
    versions = _get_versions(repo_name)
    new_versions = _get_current_versions(repo_name)
    if versions == new_versions:
        indexing['skipped'] += 1
        print 'skipping', repo_name
        return

    indexing['cur'].add(repo_name)
    print 'start', repo_name, indexing

    if versions.get('wiki') != new_versions['wiki']:
        index_wiki(repo_name)
#        print 'updating wiki', versions.get('wiki'), wiki_version
        new_versions['dirty'] = True
    if versions.get('gh_pages') != new_versions['gh_pages']:
#        print 'updating gh_pages', versions.get('gh_pages'), gh_pages_version
        index_gh_pages(repo_name)
        new_versions['dirty'] = True
    if versions.get('readme') != new_versions['readme']:
#        print 'updating readme', versions.get('readme'), readme_version
        index_readme(repo_name)
        new_versions['dirty'] = True

    _set_versions(repo_name, new_versions)

    indexing['cur'].remove(repo_name)
    indexing['tot'] += 1
    print 'finish', repo_name, indexing

    # # add autocomplete data for repo
    # page_count = len(bulk_rows)/2
    # repo_id = urllib.quote(repo_name, '')

    # bulk_rows += [{
    #     "index": {
    #         "_index": "autocomplete", "_type": "repo", "_id": repo_id
    # }},
    # {
    #     'owner': user,
    #     'repo': repo,
    #     'count': page_count
    # }]

#    return {'user': user, 'page_count':page_count, 'bulk_rows': bulk_rows}

def index_wiki(repo_name):
    """ return bulk rows for wiki for repo_name repo """
    # get and parse a list of all wiki page urls
    url_template = '%s/%s/wiki/_pages'
    url = url_template % (settings.GITHUB_HOST, repo_name)
    html = urllib3.request('get', url).data
    strainer = SoupStrainer(id='wiki-content')
    soup = BS(html, 'lxml', parse_only=strainer)
    if not soup.ul:
        return []
    page_links = soup.ul.find_all('a')
    page_urls = (settings.GITHUB_HOST + link.get('href') for link in page_links)

    # index each page
    jobs = [pool.spawn(index_wiki_page, repo_name, page_url) for page_url in page_urls]
    gevent.joinall(jobs)
    _rerase(jobs)
    bulk_rows = [row for job in jobs for row in job.value]
    _write_bulk_rows(repo_name, 'wiki', bulk_rows)

def index_wiki_page(repo_name, page_url):
    """ return bulk rows for wiki page at page_url for repo_name repo """
    html = urllib3.request('get', page_url).read()
    strainer = SoupStrainer(id='wiki-wrapper')
    soup = BS(html, 'lxml', parse_only=strainer)
    path = urlparse(page_url).path[1:]
    page_id = urllib.quote(path, '')  # remove initial slash
    return ({
        "index": {
            "_index": "docs", "_type": "wiki_page", "_id": page_id
    }},
    {
        'url': page_url,
        'title': ' '.join(soup.find(id='head').h1.findAll(text=True)),
        'content': ' '.join(soup.find(id='wiki-content').findAll(text=True)),
        'repo': '/' + repo_name
    },)

def index_readme(repo_name):
    url_template = '%s/%s/'
    url = url_template % (settings.GITHUB_HOST, repo_name)
    html = urllib3.request('get', url).data
    strainer = SoupStrainer(id='readme')
    soup = BS(html, 'lxml', parse_only=strainer)
    path = urlparse(url).path[1:]  # remove initial slash
    page_id = urllib.quote(path, '')

    # if there is no readme, skip
    try:
        title = ' '.join(soup.find(class_='name').findAll(text=True))
        content = ' '.join(soup.find('article').findAll(text=True))
    except AttributeError:
        _write_bulk_rows(repo_name, 'readme', [])
        return

    bulk_rows = ({
        "index": {
            "_index": "docs", "_type": "readme", "_id": page_id
    }},
    {
        'url': url,
        'title': title,
        'content': content,
        'repo': '/' + repo_name
    },)
    _write_bulk_rows(repo_name, 'readme', bulk_rows)


def index_gh_pages(repo_name):
    """ return bulk rows for github pages for repo_name repo """
    url_template = '%s/pages/%s/'
    url = url_template % (settings.GITHUB_HOST, repo_name)
    bulk_rows = index_gh_page(url, repo_name, url, set())
    _write_bulk_rows(repo_name, 'gh_pages', bulk_rows)

def index_gh_page(page_url, repo_name, base_url, already_visited):
    """
    return bulk rows for github page and all linked github pages
    that haven't already been visited
    """
    def gen_url(link):
        url = urljoin(page_url, link.get('href'))
        # normalize url by removing index.*
        split_url = url.rsplit('/', 1)
        if len(split_url) > 1 and split_url[-1].startswith('index.'):
            url = split_url[0]
        url = url.split('#', 1)[0]
        return url

    def valid_url(url):
        # only index pages that have not already been indexed and that are in a gh_pages subfolder
        if not url or url in already_visited or not url.startswith(base_url):
            return False
        already_visited.add(url)
        return True

    try:
        resp = urllib3.request('get', page_url)
    except:
        return []
    if resp.headers.get('content-type') != 'text/html':
        return []
    html = resp.data
    try:
        soup = BS(html, 'lxml')
    except:
        return []
    links = soup.find_all('a')
    child_urls = (gen_url(link) for link in links)
    child_urls = [url for url in child_urls if valid_url(url)]
    jobs = [pool.spawn(index_gh_page, child_url, repo_name, base_url, already_visited) for child_url in child_urls]
    gevent.joinall(jobs)
    _rerase(jobs)

    bulk_rows = [row for job in jobs for row in job.value]
    page_id = urllib.quote(urlparse(page_url).path[1:], '')
    title = soup.find('title')
    title = title.text if title else page_url
    bulk_rows += [{
            "index": {
                "_index": "docs", "_type": "gh_page", "_id": page_id
        }},
        {
            'url': page_url,
            'title': title,
            'content': _get_visible_text(soup),
            'repo': '/' + repo_name
    }]
    return bulk_rows

def index_all_users(repo_data):
    """
    given a lst of repo_data containing page_count and user for each repo
    retur bulk_rows for user autocomplete
    """
    users = {}
    for item in repo_data:
        users.setdefault(item['user'], 0)
        users[item['user']] += item['page_count']

    bulk_rows = []
    for user, page_count in users.items():
            bulk_rows.append({
                "index": {
                    "_index": "autocomplete", "_type": "user", "_id": user
            }})
            bulk_rows.append({
                'owner': user,
                'count': page_count
            })
    return bulk_rows

    def index_all_jira_issues(self):
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

        # Grab almost all data via API calls, 500 issues at a time
        while True:
            json_result = urllib2.urlopen("%s&startAt=%d&maxResults=%d&" % (jira_url, offset, max_results)).read()
            json_parsed = json.loads(json_result)
            issues += json_parsed['issues']
            if json_parsed["total"] > len(issues):
                offset += max_results
            else:
                break

        bulk_data_obj = []

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

            for comment in issue['fields']['comment']['comments']:
                index['_id'] = comment['id']
                obj['content'] = comment['body']
                if 'author' in comment.keys():
                    obj['author'] = comment['author']['name']
                else:
                    obj['author'] = None
                obj['created_date'] = comment['created']
                obj['title'] = "Comment for Jira issue %s" % issue['key']
                obj['url'] = "%s/browse/%s?focusedCommentId=%s" % (settings.JIRA_HOST, issue['key'], comment['id'])
                obj['status'] = None
                obj['path'] = "%s/%s" % (issue['fields']['project']['key'], issue['key'])

                bulk_data_obj.append({'index': index})
                bulk_data_obj.append(obj)

        # submit the issues to elasticsearch
        bulk_data = '\n'.join([json.dumps(row) for row in bulk_data_obj]) + '\n'
        resp = es_client._bulk.post(data=bulk_data)
        es_client._refresh.post()
        return resp

def _get_visible_text(soup):
    texts = soup.findAll(text=True)

    def visible(element):
        if element.parent.name in ['style', 'script', '[document]', 'head', 'title']:
            return False
        elif isinstance(element, bs4.element.Comment):
            return False
        return True

    return ' '.join(filter(visible, texts))

def _get_versions(repo_name):
    cache_path = path.join(CACHE, repo_name)
    versions_path = path.join(cache_path, 'versions')
    try:
        with open(versions_path, 'r') as f:
            return json.load(f)
    except IOError:
        try:
            os.makedirs(cache_path)
        except:
            pass
        return {}

def _set_versions(repo_name, versions):
    dirty = versions.pop('dirty', False)

    if dirty:
        versions_path = path.join(CACHE, repo_name, 'versions')
        with open(versions_path, 'w') as f:
            return json.dump(versions, f)

def _write_bulk_rows(repo_name, typ, bulk_rows):
url = 'http://localhost:8080/search/wiki/%s/_query' % typ
data = {"query":
    {
      "filtered": {
        "filter": {
          "term": {
            "repo.path": "/%s" % repo_name
          }
        }
      }
    }
}

json = urllib3.request('delete', url, body=data).data

    # cache_path = path.join(CACHE, repo_name, typ)

    # with open(cache_path, 'w') as f:
    #     gevent.os.make_nonblocking(f)
    #     out = '\n'.join([json.dumps(row) for row in bulk_rows]) + '\n'
    #     gevent.os.nb_write(f.fileno(), out)

def _get_current_versions(repo_name):
    commands = [
        'git ls-remote https://github.cfpb.gov/%s.wiki.git HEAD' % repo_name,
        'git ls-remote https://github.cfpb.gov/%s.git -b gh-pages' % repo_name,
        'git ls-remote https://github.cfpb.gov/%s.git HEAD' % repo_name,
    ]
    procs = [subprocess.Popen(command.split(), stdout=subprocess.PIPE) for command in commands]
    gevent.wait(procs, timeout=3)
    return {
        'wiki': procs[0].stdout.read().split('\t')[0],
        'gh_pages': procs[1].stdout.read().split('\t')[0],
        'readme': procs[2].stdout.read().split('\t')[0],
    }

def _rerase(jobs):
    if any([job.exception for job in jobs]):
        raise BaseException('sub-gevent error')

prev_string = None
def _update_status(indexing):
    global prev_string
    if prev_string:
        print '\r' * len(prev_string),
    prev_string = 'tot: %04d   new: %04d   skipped: %04d' % (indexing['tot'] + indexing['skipped'], indexing['tot'], indexing['skipped'])

indexing = {'tot': 0, 'cur':set(), 'skipped': 0}

if __name__ == "__main__":
    index_all_repos()
    index_all_jira_issues()
    with open(LOG, 'a') as log:
        log.write('%s - synced\n' % datetime.utcnow().isoformat())
