github-wiki-search
==================

Installation
------------

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

    /vagrant/provision.py

1. visit the search page at

    http://localhost:8080
