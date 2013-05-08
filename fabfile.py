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

env.use_ssh_config = False
env.keepalive = True
env.connection_attempts = 30
env.warn_only = 1
env.output_prefix = 1

env.supported = ['precise']

if not 'mode' in env:
    env.mode = None
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

if 'vagrant' in env.tasks and 'ec2' in env.tasks:
    print(yellow('Please specify only ONE mode.'))
    exit(1)


@task
def ec2():
    env.mode = 'ec2'


@task
def standalone():
    env.mode = 'standalone'


@task
@with_settings(hide('everything'), warn_only=True)
def vagrant():
    """Get information about current Vagrant dev environment"""
    env.mode = 'vagrant'
    running = local('vagrant status | sed 1,2d | head -n 1 | grep running | tr -s \' \' | awk \'{print $1}\'', capture=True).splitlines()
    if running:
        for vm in running:
            ssh_info = local('vagrant ssh-config %s' % vm, capture=True).splitlines()[1:]
            vagrant_info = dict([l.strip().split(' ', 1) for l in ssh_info if l.strip()])
            env.key_filename = vagrant_info['IdentityFile'].strip('"')
            env.hosts.append('%(User)s@%(HostName)s:%(Port)s' % vagrant_info)
            pprint(env.hosts)
    else:
        print(red('Please start the VM with `vagrant up {0}` first. Exiting.'.format(config['VAGRANT']['HOST'])))
        exit(1)


@task
def bootstrap():
    if not env.mode:
        print(yellow('Please specify which mode to use:'))
        print(yellow('$> fab [ec2|vagrant] bootstrap.'))
        exit(1)
    if env.mode == 'ec2':
        chef_ip = _create_chef_instance_ec2()
        env.user = config['AWS']['AWS_SSH_USER']
        if not env.dry:
            if chef_ip:
                env.hosts.append(chef_ip)
                execute(_install_chef_server, chef_ip)
            print(green('\nChefabulous instance has been deployed.\n'))
            print(green('Log with:\n'))
            print(green('$> ssh -i {0} {1}@{2}\n'.format(creds['AWS']['IDENTITY_FILE'], config['AWS']['AWS_SSH_USER'], chef_ip)))
        else:
            print(cyan("Would have moved on with provisioning of the Chef server."))
    elif env.mode == 'vagrant':
        if run('hostname').succeeded:
            host = run('hostname')
            if not re.match('^{0}$'.format(config['VAGRANT']['HOST']), host):
                print(yellow("Please make sure that the VM host match the settings."))
                print(yellow('Settings say "{0}" and VM reports "{1}"'.format(config['VAGRANT']['HOST'], host)))
                print(yellow('\nBailing out by precaution.\n'))
                exit(1)
            else:
                _install_chef_server()
    else:
        print(red('Could not SSH into the Vagrant VM.'))
        print(red('Bailing out.'))


@task
def nuke():
    if not env.mode:
        print(yellow('Please specify which mode to use:'))
        print(yellow('$> fab [ec2|vagrant] bootstrap.'))
        exit(1)
    if env.mode == 'ec2':
        _delete_chef_instance_ec2()
    if env.mode == 'vagrant':
        _delete_chef_instance_vagrant()


def _delete_chef_instance_ec2():
    ec2_connection = _get_ec2_connection()
    print('Connected to {0}'.format(str(ec2_connection).split(":")[1]))
    check_if_exists = ec2_connection.get_all_instances(filters={'tag-key': config['AWS']['AWS_TAG_NAME']})
    #for reservation in check_if_exists:
    #    print(reservation.instances[0].id)
    if check_if_exists:
        print(yellow('Chefabulous instance(s) found. Proceeding with deletion (30 secs timeout)...'))
        ec2_connection.terminate_instances([reservation.instances[0].id for reservation in check_if_exists])
        for reservation in check_if_exists:
            instance = reservation.instances[0]
            if not instance.state == u'terminated':
                print(green('Waiting for instance {0} to shutdown...'.format(instance.id)))
                timeout = 0
                while(instance.state == u'running') and timeout != 30:
                    time.sleep(5)
                    timeout += 5
                    instance.update()
                timeout = 0
                while(instance.state == u'stoping' or instance.state == u'shutting-down') and timeout != 30:
                    time.sleep(5)
                    instance.update()
                    print(yellow("Instance {0} state: {1}".format(instance.id, instance.state)))
                    timeout += 5
                    if instance.state == u'terminated':
                        timeout = 30
                        print(green("Chefabulous instance {0} has been terminated.".format(instance.id)))
            else:
                print(yellow("Chefabulous instance {0} has been terminated.".format(instance.id)))
            instance.update()
            ec2_connection.delete_tags([instance.id], {config['AWS']['AWS_TAG_NAME']: ''})
            try:
                print('Attempting to delete {0} security group...'.format(config['AWS']['AWS_SEC_GROUP']))
                ec2_connection.delete_security_group(config['AWS']['AWS_SEC_GROUP'], "Chefabulous security group")
                instance.update()
                ec2_connection.delete_security_group(config['AWS']['AWS_SEC_GROUP'], "Chefabulous security group")
                print(green('...{0} security group has been deleted.'.format(config['AWS']['AWS_SEC_GROUP'].title())))
            except boto.exception.EC2ResponseError:
                print(yellow("Could not find {0} security group... Perhaps it's already been deleted ?".format(config['AWS']['AWS_SEC_GROUP'].title())))
            print(green('\nChefabulous is no more. Sad face.'))
    else:
        print(green('Could not find any Chefabulous instances tagged...'))
        print(green('\nChefabulous is no more. Sad face.'))


def _delete_chef_instance_vagrant():
    local('vagrant destroy {0} --force'.format(config['VAGRANT']['HOST']))


def _create_chef_instance_ec2():
    ec2_connection = _get_ec2_connection()
    print('Connected to {0}'.format(str(ec2_connection).split(":")[1]))
    try:
        print('Attempting to create {0} security group...'.format(config['AWS']['AWS_SEC_GROUP']))
        if not env.dry:
            ec2_connection.create_security_group(config['AWS']['AWS_SEC_GROUP'], "Chefabulous security group")
            print(green('...created.'))
        else:
            print(cyan("... but we're in DRY RUN mode."))
    except boto.exception.EC2ResponseError:
        print('...but {0} security group already exists. Moving on.'.format(config['AWS']['AWS_SEC_GROUP']))
    check_if_exists = ec2_connection.get_all_instances(filters={'tag-key': config['AWS']['AWS_TAG_NAME']})
    for reservation in check_if_exists:
        print(reservation.instances[0].id)
    if check_if_exists:
        print(yellow('Previous Chefabulous instance(s) were found...'))
        for reservation in check_if_exists:
            instance = reservation.instances[0]
            if not instance.state == u'terminated':
                if instance.state == u'stoping' or instance.state == u'shutting-down':
                    print instance.state
                    print(yellow('Waiting 30s for previous Chefabulous state to be either terminated or stopped.'))
                    timeout = 0
                    while(instance.state == u'stoping' or instance.state == u'shutting-down') and timeout != 30:
                        time.sleep(5)
                        timeout += 5
                elif instance.state == u'running':
                    print(red('...only one Chefabulous should be created.'))
                    if instance.public_dns_name:
                        print('Public DNS of the previous one: {0}'.format(instance.public_dns_name))
                    _ips_perms(ec2_connection, config['AWS']['AWS_SEC_GROUP'])
                    exit(1)
                else:
                    print(red('Could not figure Chefabulous instance state. Bailing out.'))
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
        ec2_connection.create_tags([instance.id], {'Name': config['AWS']['AWS_NODE_NAME'],
                                                   config['AWS']['AWS_TAG_NAME']: ''})
        while instance.state == u'pending':
            print(yellow("Instance {0} state: {1}".format(instance.id, instance.state)))
            time.sleep(10)
            instance.update()
        print(green("Instance {0} state: {1}".format(instance.id, instance.state)))
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


def _install_chef_server(chef_ip=None):
    if env.host == '127.0.0.1':
        env.current = '{0} VM'.format(config['VAGRANT']['HOST'])
    else:
        env.current = env.host
    print(green('Proceeding with Chef server install on {0}'.format(env.current)))
    if (deb.distrib_codename().succeeded):
        print(green('--> Checking for distrib codename on %s' % env.current))
        distrib = deb.distrib_codename()
        if distrib not in env.supported:
            print(red('Please use a supported distribution.'))
            exit(1)
    else:
        print(yellow('Only Ubuntu is supported at the current moment.'))
        exit(1)
    deb.update_index(quiet=True)
    deb.upgrade(safe=True)
    require.files.directory('chefabulous', mode=755)
    with cd('chefabulous'):
        require.files.file(url='https://opscode-omnibus-packages.s3.amazonaws.com/ubuntu/12.04/x86_64/chef-server_11.0.8-1.ubuntu.12.04_amd64.deb',
                           md5='076bfc8409ef2bc1818c9c515b472b82',
                           verify_remote=True,
                           mode=755)
        if not deb.is_installed('chef-server'):
            print(yellow('Chef server is not installed.'))
            sudo('dpkg -i chef-server_11.0.8-1.ubuntu.12.04_amd64.deb')
    if not files.is_dir('/etc/chef-server'):
        if sudo('chef-server-ctl reconfigure').succeeded:
            print(green('Chef server has been configured on {0}!'.format(env.current)))
