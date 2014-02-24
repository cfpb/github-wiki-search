#! /usr/bin/python
import os
from os.path import join
from os import path
from subprocess import call, Popen

DIR = path.dirname(path.realpath(__file__))

try:
    # update and upgrade all packages
    call('sudo apt-get update -y'.split())
    call('sudo apt-get upgrade -y'.split())
    # install java
    call('sudo apt-get install curl openjdk-7-jre-headless -y'.split())
except OSError:
    # if apt isn't installed, need to run yum commands
    pass

#install elastic search
if 'elasticsearch-1.0.0.tar.gz' not in os.listdir(DIR):
    call(['wget', 'https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.0.0.tar.gz'])
    call(['tar', '-xvzf', join(DIR, 'elasticsearch-1.0.0.tar.gz')])

    # install git river
    call('bin/plugin --install com.bazoud.elasticsearch/elasticsearch-river-git/0.0.2'.split())

# start elasticsearch
Popen(join(DIR, 'elasticsearch-1.0.0/bin/elasticsearch'))
