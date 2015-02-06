#! /usr/bin/python


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
