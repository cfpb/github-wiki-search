#! /usr/bin/python
import os
from os.path import join
from os import path
from subprocess import call

DIR = path.dirname(path.realpath(__file__))


call('sudo yum update -y'.split())
#install java
call('sudo yum install java-1.7.0-openjdk-devel -y'.split())
# install dev packages
call('sudo yum install wget git gcc python-pip python-devel.x86_64 libxslt-devel.x86_64 libxslt-python.x86_64 libxml2-devel.x86_64 libxml2-python.x86_64 -y'.split())
# add EPEL repo
call('sudo rpm -Uvh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm'.split())
# install nginx
call('sudo yum install -y nginx'.split())

# install elasticsearch key and repo
call('rpm --import http://packages.elasticsearch.org/GPG-KEY-elasticsearch'.split())
call(['sudo', 'cp', join(DIR, 'elasticsearch.repo'), '/etc/yum.repos.d/elasticsearch.repo'])
#install elastic search
call('sudo yum install -y elasticsearch.noarch'.split())

# # if yum isn't installed, need to run apt commands - this is no longer maintained
# # but need to update to use elasticsearch repo (http://www.elasticsearch.org/blog/apt-and-yum-repositories/)
# # update and upgrade all packages
# call('sudo apt-get update -y'.split())
# call('sudo apt-get upgrade -y'.split())
# # install java
# call('sudo apt-get install curl openjdk-7-jre-headless -y'.split())
# # install python developer packages
# call('sudo apt-get install python-dev python-pip libxml2-dev libxslt1-dev -y'.split())
# # install nginx
# call('sudo apt-get install nginx'.split())

# copy over nginx config file
with open(join(DIR, 'nginx.conf.template'), 'r') as conf_file:
    nginx_conf = conf_file.read() % DIR

tmp = join(DIR, 'nginx.conf.tmp')
with open(tmp, 'w') as conf_file:
    conf_file.write(nginx_conf)

call(('sudo cp %s /etc/nginx/nginx.conf' % tmp).split())

os.remove(tmp)

# start nginx
call('sudo service nginx start'.split())

# start on startup
call('sudo chkconfig nginx on'.split())

call('sudo service elasticsearch start'.split())

# start on startup
call('sudo chkconfig elasticsearch on'.split())

# install python dependencies
call('sudo pip install -r requirements.txt'.split())
