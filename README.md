# Chefabulous
===========

## What ?

Bootstrap a [Chef](http://docs.opscode.com/chef_quick_overview.html) server on [Amazon's EC2](https://console.aws.amazon.com/ec2) **or** using [Vagrant](http://www.vagrantup.com/). 

Inspired by [knife-server](http://fnichol.github.io/knife-server/) from [Fletcher Nichol](https://github.com/fnichol).



## Why ?

I'm a huge fan of [Fabric](http://docs.fabfile.org/en/1.6/) and a quick way to spin up a new Chef server instance on EC2 or Vagrant for tests.

[knife-server](http://fnichol.github.io/knife-server/) is a **better** tool, but you might like the lack of features of Chefabulous.

But hey, feel free to [contribute](https://github.com/scalp42/chefabulous#need-help-or-want-to-contribute-) :)

## How ?

### Requirements:

- Python 2.7, with the following packages:
	- [fabric](http://docs.fabfile.org)
	- [fabtools](https://fabtools.readthedocs.org)
	- [boto](http://docs.pythonboto.org)
- [Vagrant](http://www.vagrantup.com/) (optional)
- [AWS credentials](https://portal.aws.amazon.com/gp/aws/securityCredentials) (optional)

### Installation (MacOsX):

1) Install Python 2.7:

	$> brew update ; brew install python
2) Add this to your .zshrc/.bash_profile and source it:

	export PYTHONPATH=$(brew --prefix)/lib/python2.7/site-packages

	export PATH=/usr/local/share/python:$PATH

3) Git clone this repository (commands from now on will be assumed running from the repository source)

4) Install [fabric](http://docs.fabfile.org) and [fabtools](https://fabtools.readthedocs.org), as well as [boto](http://docs.pythonboto.org) for AWS EC2:

	$> pip install -r requirements.txt
5) Set your credentials (see [credentials section](https://github.com/scalp42/chefabulous#credentialsyml) for more details)

	cp credentials.yml.example credentials.yml
6) Set your settings in `settings.yml` (see [settings section](https://github.com/scalp42/chefabulous#settingsyml) for more details)

7) A `.rvmrc` and `Gemfile` is provided to help you install Vagrant

	$> bundle install
	
7) Make sure the `Vagrant` VM host matches ['VAGRANT']['HOST'] (see [vagrant settings](https://github.com/scalp42/chefabulous#vagranthost-chefabulous))

### Usage:
	
	$> fab [vagrant|ec2] [bootstrap|nuke]
	
	
### Configuration:

##### Settings.yml

###### ['AWS']['AWS_DRY_RUN']: [True|False]

If set to `True`, no instance will be created on AWS EC2. Allows to test AWS credentials.

###### ['AWS']['AWS_NODE_NAME']: 'name'

The name of the instance on AWS EC2.

###### ['AWS']['AWS_REGION']: 'us-west-1'

The region to deploy to for AWS EC2.

###### ['AWS']['AWS_AVAILABILITY_ZONE']: 'us-west-1a'

The availability zone for the specified zone.

###### ['AWS']['AWS_IMAGE']: 'ami-2928076c'

The AMI to deploy. Default to Ubuntu 12.04 LTS EBS backed. Only this AMI has been tested.

###### ['AWS']['AWS_FLAVOR']: 't1.micro'

The "flavor" of the instance (understand CPU, memory etc). Please refer to [AWS EC2 Instance Types](http://aws.amazon.com/ec2/instance-types/) and [AWS AMI Instance Type Matrix](http://aws.amazon.com/amazon-linux-ami/instance-type-matrix/).

###### ['AWS']['AWS_SSH_USER']: 'ubuntu'

The user used to log in in the instance. Defaults to 'ubuntu' and should not be modified.

###### ['AWS']['AWS_SEC_GROUP']: 'chefabulous'

The name of the security group used by Chefabulous on AWS EC2. Can be modified without any consequences, just visual.

###### ['AWS']['AWS_TAG_NAME']: 'chefabulous'

This parameter is **highly** important. It's used to determine if a Chefabulous instance is already running or not.

###### [VAGRANT]['HOST']: 'chefabulous'

This paramater is used in Vagrant mode and act as a safeguard. It should match the VM hostname in the `Vagrantfile`.


###### ['AWS_SEC_IPS']['ruleX']

The rules will be added to ['AWS']['AWS_SEC_GROUP'] configured. By default, only 22 (SSH) and 443 (Chef-server) are allowed.


##### Credentials.yml

###### ['AWS']['AWS_ACCESS_KEY_ID']: 'accesskeyid'

Your [AWS Access Key Id](https://portal.aws.amazon.com/gp/aws/securityCredentials).

###### ['AWS']['AWS_SECRET_ACCESS_KEY']: 'secretaccesskey'

Your [AWS Secret Access Key](https://portal.aws.amazon.com/gp/aws/securityCredentials).

###### ['AWS']['AWS_KEY_NAME']: 'keypair-name-on-EC2'

The name of your keypair on AWS EC2.

###### ['AWS']['IDENTITY_FILE']: '~/.ssh/id_rsa_aws'

The private key associated to your keypair on AWS EC2.




## Roadmap:

- clean output
- add safety checks regarding lack of AWS creds etc
- create a PyPI package with 'chefabulous' binary/script
- support ubuntu 10.04
- support multiple chef server versions
- allow WebUI password to be modified in settings
- robust Chef server provisioning
- add an option to override the cidr for SSH access limited to the host running chefabulous






## Need Help or Want to Contribute ?

All contributions are welcome: ideas, patches, documentation, bug reports, complaints, and even something you drew up on a napkin.

It is more important to me that you are able to contribute and get help if you need it.

That said, some basic guidelines, which you are free to ignore :)

- Have a problem you want [**chefabulous**](https://github.com/scalp42/chefabulous) to solve for you ? You can email me personally (scalisia@gmail.com)
- Have an idea or a feature request? File a [ticket on Github](https://github.com/scalp42/chefabulous/issues/new), or email me personally (scalisia@gmail.com) if that is more comfortable.
- If you think you found a bug, it probably is a bug. Please file a [ticket on Github](https://github.com/scalp42/chefabulous/issues/new).
- If you want to contribute, best way is to fork this repo and send me a pull request. If you don't know git, I also accept diff(1) formatted patches - whatever is most comfortable for you.

**Programming is not a required skill. Whatever you've seen about open source with maintainers or community members saying "send patches or die" -  you will not see that here.**