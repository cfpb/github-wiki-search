:warning: We are no longer maintaining this repo :warning:

# GitHub Wiki Search

While this project started as a github wiki search (hence the repo name),
it has morphed into a search-multiple-sources-of-relevant-information search.

It can search:
  * Github.com
    * Issues
    * Github Pages
    * Wiki
    * Readmes
  * Github Enterprise
    * Issues
    * Github Pages
    * Wiki
    * Readmes
  * Jira
    * Issues

There is no app backend: the frontend code talks directly to Elasticsearch.
This works OK in a particular setting, but probably isn't a good idea in general.

Repo highlights:

  * `client/`: where the web app lives – javascript, html, mustache templates.
  * `server/`: a misnomer – a set of Python scripts for getting the data into Elasticsearch

## Getting started

### Run locally with `docker-compose`

You can start all components of the app with `docker-compose up`. Once the
containers are running, you should be able to see the frontend at
http://localhost:80, but there will be no data in Elasticsearch at this
point

Right now, unfortunately, the container that does the indexing is
really geared toward running in production, rather than local dev, and its
entrypoint runs the indexing on a cron schedule. What's more, the config
the indexer needs to talk to the data sources that get indexed is not
present (in production the config is provided via env vars and secrets
furnished by the container platform hosting the app, _eg_ DC/OS). All of
this means that currently, for local dev, it's not easy to get some data
into ES to test against.

A nice future improvement would be to modify the indexer container's
setup to make it more amenable to getting data into ES for local dev,
and/or providing some fixture data.

### Note about `docker-machine`

If you're using `docker-machine` instead of Docker Engine and see this error:

```
max virtual memory areas vm.max_map_count [65530] is too low, increase to at least [262144]
```

`docker-machine ssh` and make the following change to `/var/lib/boot2docker/profile`:

```
sysctl -w vm.max_map_count=262144
```

### Rebuilding the Index

If your index isn't updating quite right, it may help to drop the index first.
One example we found of this is where the mapping file wasn't updating correctly
during the index process unless we dropped the index beforehand.

1. Drop the existing index:

```
curl -XDELETE http://[hostname]/search/_all/_all/
```

1. Run the python script to rebuild everything:

```
./server/index.py
```


## Contributing

We welcome your feedback and contributions.

- [Find out about contributing](https://github.com/cfpb/github-wiki-search/blob/master/CONTRIBUTING.md)
- [File a bug](https://github.com/cfpb/github-wiki-search/issues/new?body=%23%23%20URL%0D%0D%0D%23%23%20Actual%20Behavior%0D%0D%0D%23%23%20Expected%20Behavior%0D%0D%0D%23%23%20Steps%20to%20Reproduce%0D%0D%0D%23%23%20Screenshot&labels=bug)

