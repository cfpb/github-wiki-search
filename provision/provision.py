#! /usr/bin/python
import os
from os.path import join
from os import path
from subprocess import call


PROVISION_DIR = path.dirname(path.realpath(__file__))
REPO_DIR = path.dirname(PROVISION_DIR)
TEMPLATE_DIR = path.join(PROVISION_DIR, 'templates')
SERVER_DIR = path.join(PROVISION_DIR, 'server')

call('yum update -y'.split())
#install java
call('yum install java-1.7.0-openjdk-devel -y'.split())
# install dev packages
call('yum install wget git gcc python-pip python-devel.x86_64 libxslt-devel.x86_64 libxslt-python.x86_64 libxml2-devel.x86_64 libxml2-python.x86_64 -y'.split())
# add EPEL repo
call('rpm -Uvh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm'.split())
# install nginx
call('yum install -y nginx'.split())

# install elasticsearch key and repo
call('rpm --import http://packages.elasticsearch.org/GPG-KEY-elasticsearch'.split())
call(['sudo', 'cp', join(TEMPLATE_DIR, 'elasticsearch.repo'), '/etc/yum.repos.d/elasticsearch.repo'])
#install elastic search
call('yum install -y elasticsearch.noarch'.split())
#install elasticsearch-head, a gui for elasticsearch
call(['sudo', '/usr/share/elasticsearch/bin/plugin', '-install', 'mobz/elasticsearch-head'])

# # if yum isn't installed, need to run apt commands - this is no longer maintained
# # but need to update to use elasticsearch repo (http://www.elasticsearch.org/blog/apt-and-yum-repositories/)
# # update and upgrade all packages
# call('apt-get update -y'.split())
# call('apt-get upgrade -y'.split())
# # install java
# call('apt-get install curl openjdk-7-jre-headless -y'.split())
# # install python developer packages
# call('apt-get install python-dev python-pip libxml2-dev libxslt1-dev -y'.split())
# # install nginx
# call('apt-get install nginx'.split())

# copy over nginx config file
with open(join(TEMPLATE_DIR, 'nginx.conf.template'), 'r') as conf_file:
    nginx_conf = conf_file.read() % REPO_DIR

tmp = join(REPO_DIR, 'nginx.conf.tmp')
with open(tmp, 'w') as conf_file:
    conf_file.write(nginx_conf)

call(('cp %s /etc/nginx/nginx.conf' % tmp).split())

os.remove(tmp)

# ensure nginx user has permission to access web files
call(('chown -R nginx %s' % os.path.join(REPO_DIR, 'client', 'dist')).split())
call(('chmod a+x %s/client' % REPO_DIR).split())
call(('chmod a+x %s' % REPO_DIR).split())
call(('chmod a+x %s' % os.path.join(REPO_DIR, '..')).split())

# start nginx/elasticsearch
call('service nginx start'.split())
call('service elasticsearch start'.split())

# start on startup
call('chkconfig nginx on'.split())
call('chkconfig elasticsearch on'.split())

# install python dependencies
call(('pip install -r %s' % path.join(REPO_DIR, 'server', 'requirements.txt')).split())

# symlink server dir into python packages
call(('ln -s %s /usr/lib/python2.6/site-packages/server' % SERVER_DIR).split())

with open(join(TEMPLATE_DIR, 'cron.template'), 'r') as conf_file:
    nginx_conf = conf_file.read() %  join(REPO_DIR, 'server', 'sync.py')

# run sync script every morning at 3 am
tmp = join(REPO_DIR, 'cron.tmp')
with open(tmp, 'w') as conf_file:
    conf_file.write(nginx_conf)

call(('cp %s /etc/cron.d/github_sync' % tmp).split())

os.remove(tmp)
