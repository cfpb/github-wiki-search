#! /usr/bin/python
import os
from os.path import join
from os import path
from subprocess import call, Popen
import settings

DIR = path.dirname(path.realpath(__file__))

try:
    # update and upgrade all packages
    call('sudo apt-get update -y'.split())
    call('sudo apt-get upgrade -y'.split())
    # install java
    call('sudo apt-get install curl openjdk-7-jre-headless -y'.split())
    # install python developer packages
    call('sudo apt-get install python-dev python-pip libxml2-dev libxslt1-dev -y'.split())
    pass
except OSError:
    # if apt isn't installed, need to run yum commands
    call('sudo yum update -y'.split())
    #install java
    call('sudo yum install java-1.7.0-openjdk-devel -y'.split())
    # install python dev packages
    call('sudo yum install gcc python-pip python26-devel.x86_64 libxslt-devel.x86_64 libxslt-python.x86_64 libxml2-devel.x86_64 libxml2-python.x86_64 -y')

#install elastic search
if 'elasticsearch-1.0.0.tar.gz' not in os.listdir(DIR):
    call(['wget', 'https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.0.0.tar.gz'])
    call(['tar', '-xvzf', join(DIR, 'elasticsearch-1.0.0.tar.gz')])

    # install git river
    # call([join(DIR, 'elasticsearch-1.0.0/bin/plugin')] + '--install com.bazoud.elasticsearch/elasticsearch-river-git/0.0.3'.split())

# start elasticsearch
Popen(join(DIR, 'elasticsearch-1.0.0/bin/elasticsearch'))

# install python dependencies
call('sudo pip install -r requirements.txt'.split())

# create wiki index with schema
import requests

with open(join(DIR, 'wiki_page_schema.json')) as f:
    schema = f.read()

requests.put(settings.ES_HOST + '/wiki', data=schema)

