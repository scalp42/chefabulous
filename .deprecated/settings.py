# EC2 settings

AWS_DRY_RUN = None

AWS_NODE_NAME = 'chefabulous'
AWS_REGION = 'us-west-1'
AWS_AVAILABILITY_ZONE = 'us-west-1a'
AWS_IMAGE = 'ami-2928076c'
AWS_FLAVOR = 't1.micro'
AWS_SSH_USER = 'ubuntu'
AWS_SEC_GROUP = 'chefabulous'

# Chefabulous security group IPs

SEC_IPS = {
    'rule1': {
        'proto': 'tcp',
        'from': 22,
        'to': 22,
        'cidr': '0.0.0.0/0'
    },
    'rule2': {
        'proto': 'tcp',
        'from': 443,
        'to': 443,
        'cidr': '0.0.0.0/0'
    },
    'rule3': {
        'proto': 'tcp',
        'from': 444,
        'to': 444,
        'cidr': '0.0.0.0/0'
    }
}
