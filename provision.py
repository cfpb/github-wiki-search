#! /usr/bin/python
import os
from os.path import join
from os import path
from subprocess import call, Popen
import settings
import time

DIR = path.dirname(path.realpath(__file__))

try:
    # update and upgrade all packages
    call('sudo apt-get update -y'.split())
    call('sudo apt-get upgrade -y'.split())
    # install java
    call('sudo apt-get install curl openjdk-7-jre-headless -y'.split())
    # install python developer packages
    call('sudo apt-get install python-dev python-pip libxml2-dev libxslt1-dev -y'.split())
    # install nginx
    call('sudo apt-get install nginx'.split())
except OSError:
    # if apt isn't installed, need to run yum commands
    call('sudo yum update -y'.split())
    #install java
    call('sudo yum install java-1.7.0-openjdk-devel -y'.split())
    # install dev packages
    call('sudo yum install git gcc python-pip python26-devel.x86_64 libxslt-devel.x86_64 libxslt-python.x86_64 libxml2-devel.x86_64 libxml2-python.x86_64 -y')
    # add EPEL repo
    call('sudo rpm -Uvh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm'.split())
    # install nginx
    call('sudo yum install -y nginx'.split())

# copy over nginx config file
    with open(join(DIR, 'nginx.conf.template'), 'r') as conf_file:
        nginx_conf = conf_file.read() % DIR
    with open('/etc/nginx/nginx.conf', 'w') as conf_file:
        conf_file.write(nginx_conf)

# start nginx
call('sudo service nginx start'.split())

# start on startup
call('sudo chkconfig nginx on'.split())

#install elastic search
if 'elasticsearch-1.0.0.tar.gz' not in os.listdir(DIR):
    call(['wget', 'https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.0.0.tar.gz'])
    call(['tar', '-xvzf', join(DIR, 'elasticsearch-1.0.0.tar.gz')])

# start elasticsearch
Popen(join(DIR, 'elasticsearch-1.0.0/bin/elasticsearch'))

# install python dependencies
call('sudo pip install -r requirements.txt'.split())

import requests

# wait until elasticsearch is started up
while True:
    print("waiting for elasticsearch to start...")
    try:
        requests.get(settings.ES_HOST)
    except requests.exceptions.ConnectionError:
        time.sleep(2)
    else:
        break
print("elastic search started")

# create wiki index with schema
with open(join(DIR, 'wiki_page_schema.json')) as f:
    schema = f.read()

requests.put(settings.ES_HOST + '/wiki', data=schema)

