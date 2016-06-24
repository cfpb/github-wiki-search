# GitHub Wiki Search

Search the contents of GitHub Enterprise wikis.


## Contributing

We welcome your feedback and contributions.

- [Find out about contributing](https://github.com/cfpb/github-wiki-search/blob/master/CONTRIBUTING.md)
- [File a bug](https://github.com/cfpb/github-wiki-search/issues/new?body=%23%23%20URL%0D%0D%0D%23%23%20Actual%20Behavior%0D%0D%0D%23%23%20Expected%20Behavior%0D%0D%0D%23%23%20Steps%20to%20Reproduce%0D%0D%0D%23%23%20Screenshot&labels=bug)


## Getting started


### Installation

1. install [vagrant](http://www.vagrantup.com/)

1. clone the repository:

    https://github.com/cfpb/github-wiki-search.git

1. install [vagrant cachier](https://github.com/fgrehm/vagrant-cachier)

    vagrant plugin install vagrant-cachier

1. enter the repo directory:

    cd github-wiki-search

1. copy `settings_example.py` to `settings.py` and modify for your installation

1. start the virtualmachine

    vagrant up

1. ssh into the virtualmachine

    vagrant ssh

1. run the provisioning script

    sudo /vagrant/provision/provision.py

1. run the sync script

    /vagrant/server/sync.py

1. visit the search page at

    http://localhost:8080


### Front end requirements

- [npm](https://npmjs.org/)
- [grunt-cli](http://gruntjs.com/getting-started)


### Install front end tools and components

1. install dependencies:

    `npm install`

1. pull in Bower components:

    `grunt vendor`


### Front end workflow

1. compile JavaScript and LESS files:

    `grunt`

1. update dist folder with newly compiled assets:

    `grunt dist`

Or use `grunt serve`. This will run both commands when commonly edited front end files have changed. It also sets up a local server on port `8000` for previewing the front end.

### Revuilding the Index

If your index isn't updating quite right, it may help to drop the index first.  One example we found of this is where the mapping file wasn't updating correctly during the index process unless we dropped the index beforehand.

1. Drop the existing index:

```
curl -XDELETE http://search.demo.cfpb.gov/search/_all/_all/
```

1. Run a python script to rebuild everything

```
./server/index.py
```
