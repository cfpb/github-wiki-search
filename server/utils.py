#! /usr/bin/python
import json
import re

def iter_get(client):
    """
    return an iterator over all results from GETing the client and any subsequent pages.
    """
    items = []
    while items or client:
        if not items:
            resp = client.get()
            items = resp.json()
            if not isinstance(items, list):
                # something went wrong - the result from github will explain.
                raise BaseException(items)
            next = resp.links.get('next', {}).get('url')
            client = client._path([next]) if next else None
        if items:
            yield(items.pop(0))

next_re = re.compile(r'<(.*)>; rel="next"')
def _get_next_url(resp):
    links = resp.headers.get('link', '')
    split_links = links.split(",")
    for item in split_links:
        next_match = next_re.match(item)
        if next_match:
            return next_match.groups()[0]

def iter_get_url(url, pool):
    """
    return an iterator over all results from GETing the url (absolute or relative) and any subsequent pages.
    """
    items = []
    while items or url:
        if not items:
            resp = pool.request('get', url)
            try:
                items = json.loads(resp.data)
            except:
                raise BaseException(resp.data)
            if not isinstance(items, list):
                # something went wrong - the result from github will explain.
                raise BaseException(items)
            url = _get_next_url(resp)
        if items:
            yield(items.pop(0))
