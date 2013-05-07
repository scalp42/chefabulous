#!/usr/bin/env python

import os
from os.path import expanduser
import re
import string
import shelve
import itertools
import simplejson
import urllib
import time
from pprint import pprint
import route53
from fabric.api import *
from fabric.colors import *
from fabric.decorators import *
from fabric.contrib import *
from fabtools import *
import boto
import boto.ec2
#from boto import *
#from boto.ec2 import *
import yaml

env.keepalive = True
env.connection_attempts = 2
env.warn_only = 1
env.output_prefix = 1

if len(env.tasks) >= 1:
    config_file = open('settings.yml', 'r')
    config = yaml.load(config_file)
    config_file.close()
    creds_file = open('credentials.yml', 'r')
    creds = yaml.load(creds_file)
    creds_file.close()

if config['AWS']['AWS_DRY_RUN']:
    print(cyan("DRY RUN MODE, no instance will be created !"))
    env.dry = True
else:
    env.dry = False


@task
def ec2():
    env.mode = 'ec2'


@task
def standalone():
    env.mode = 'standalone'


@task
def vagrant():
    env.mode = 'vagrant'


@task
def bootstrap():
    if not env.mode:
        print(yellow('\t-> Please make sure ec2/standalone modes.'))
        print(yellow('\t-> Assuming EC2 mode.'))
        env.mode = 'ec2'
    if env.mode == 'ec2':
        chef_ip = _create_chef_instance()
        env.user = config['AWS']['AWS_SSH_USER']
        if not env.dry:
            if chef_ip:
                env.hosts.append(chef_ip)
                execute(_install_chef_server, chef_ip)
        else:
            print(cyan("Would have moved on with provisioning of the Chef server."))


def _create_chef_instance():
    ec2_connection = _get_ec2_connection()
    print('Connected to {0}'.format(str(ec2_connection).split(":")[1]))
    try:
        print('Attempting to create {0} security group...'.format(config['AWS']['AWS_SEC_GROUP']))
        if not env.dry:
            ec2_connection.create_security_group(config['AWS']['AWS_SEC_GROUP'], "Chefabulous security group")
        else:
            print(cyan("... but we're in DRY RUN mode."))
    except boto.exception.EC2ResponseError:
        print('...but {0} security group already exists. Moving on.'.format(config['AWS']['AWS_SEC_GROUP']))
    check_if_exists = ec2_connection.get_all_instances(filters={'tag-key': 'chefabulous'})
    if check_if_exists:
        print(yellow('Chefabulous instance already exists. Bailing out.'))
        instance = check_if_exists[0].instances[0]
        if instance.public_dns_name:
            print('Public DNS of the previous one: {0}'.format(instance.public_dns_name))
            _ips_perms(ec2_connection, config['AWS']['AWS_SEC_GROUP'])
        exit(1)
    if env.dry:
        print(cyan('Instance would have been created with the following settings:'))
        print(cyan("{0} {1} {2} {3} {4}".format(config['AWS']['AWS_IMAGE'],
                                                creds['AWS']['AWS_KEY_NAME'],
                                                config['AWS']['AWS_SEC_GROUP'],
                                                config['AWS']['AWS_AVAILABILITY_ZONE'],
                                                config['AWS']['AWS_FLAVOR'])))
    else:
        reservation = ec2_connection.run_instances(config['AWS']['AWS_IMAGE'],
                                                   key_name=creds['AWS']['AWS_KEY_NAME'],
                                                   security_groups={config['AWS']['AWS_SEC_GROUP']: None},
                                                   placement=config['AWS']['AWS_AVAILABILITY_ZONE'],
                                                   instance_type=config['AWS']['AWS_FLAVOR'])
        instance = reservation.instances[0]
        ec2_connection.create_tags([instance.id], {'Name': 'Chefabulous',
                                                   config['AWS']['AWS_NODE_NAME']: ''})
        while instance.state == u'pending':
            print(yellow("Instance state: %s" % instance.state))
            time.sleep(10)
            instance.update()
        print(green("Instance state: %s" % instance.state))
        print(green("Public DNS: %s" % instance.public_dns_name))

        _ips_perms(ec2_connection, config['AWS']['AWS_SEC_GROUP'])

        return instance.public_dns_name


def _ips_perms(conn, sec_name):
    #for i in conn.get_all_security_groups():
    #    if i.name == sec_name:
    #        sgs = [i]
    sgs = [i for i in conn.get_all_security_groups() if i.name == sec_name]
    if len(sgs) == 0:
        print(yellow('Could not find {0} security group. Creating it...'.format(config['AWS']['AWS_SEC_GROUP'])))
        conn.create_security_group(config['AWS']['AWS_SEC_GROUP'], "%s security group" % config['AWS']['AWS_SEC_GROUP'])
    print('Found {0} rules to add to {1} security group.'.format(len(config['AWS_SEC_IPS'].keys()), config['AWS']['AWS_SEC_GROUP']))
    for i in config['AWS_SEC_IPS']:
        try:
            print("Rule proto: %s, from %s, to %s, cidr %s..." % (config['AWS_SEC_IPS'][i]['proto'], config['AWS_SEC_IPS'][i]['to'], config['AWS_SEC_IPS'][i]['from'], config['AWS_SEC_IPS'][i]['cidr']))
            sgs[0].authorize(ip_protocol=config['AWS_SEC_IPS'][i]['proto'],
                             from_port=config['AWS_SEC_IPS'][i]['from'],
                             to_port=config['AWS_SEC_IPS'][i]['to'],
                             cidr_ip=config['AWS_SEC_IPS'][i]['cidr'])
            print(green("... added."))
        except boto.exception.EC2ResponseError:
            print(yellow('... already exist. Skipping it.'))


def _get_ec2_connection():
    return boto.ec2.connect_to_region(config['AWS']['AWS_REGION'],
                                      aws_access_key_id=creds['AWS']['AWS_ACCESS_KEY_ID'],
                                      aws_secret_access_key=creds['AWS']['AWS_SECRET_ACCESS_KEY'])


def _install_chef_server(chef_ip):
    pprint(env.hosts)

    if (deb.distrib_codename().succeeded):
        print(green('--> Checking for distrib codename on %s' % env.host))
        distrib = deb.distrib_codename()
    print distrib
