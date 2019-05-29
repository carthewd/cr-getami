import boto3
import crhelper
import re
import requests


# initialise logger
logger = crhelper.log_config({"RequestId": "CONTAINER_INIT"})
logger.info('Logging configured')
# set global to track init failures
init_failed = False

try:
    # Place initialization code here
    logger.info("Container initialization completed")
except Exception as e:
    logger.error(e, exc_info=True)
    init_failed = e

def create(event, context):
    """
    Place your code to handle Create events here.
    
    To return a failure to CloudFormation simply raise an exception, the exception message will be sent to CloudFormation Events.
    """
    physical_resource_id = 'getAMI'

    ami_input = re.split(r'([a-zA-Z]+)', event['ResourceProperties']['OS'])

    if ami_input[2] == '':
        amiid = get_ami(ami_input[1].lower())
    else:
        amiid = get_ami(ami_input[1].lower(), ami_input[2])


    if amiid is None: 
        raise ValueError('No AMI found matching {}.'.format(event['ResourceProperties']['OS']))

    response_data = {'AmiId': amiid}

    return physical_resource_id, response_data


def update(event, context):
    """
    Place your code to handle Update events here
    
    To return a failure to CloudFormation simply raise an exception, the exception message will be sent to CloudFormation Events.
    """

    ami_input = re.split(r'([a-zA-Z]+)', event['ResourceProperties']['OS'])

    if ami_input[2] == '':
        amiid = get_ami(ami_input[1].lower())
    else:
        amiid = get_ami(ami_input[1].lower(), ami_input[2])


    if amiid is None: 
        raise ValueError('No AMI found matching {}.'.format(event['ResourceProperties']['OS']))

    response_data = {'AmiId': amiid}
    physical_resource_id = event['PhysicalResourceId']

    return physical_resource_id, response_data


def delete(event, context):
    """
    Place your code to handle Delete events here
    
    To return a failure to CloudFormation simply raise an exception, the exception message will be sent to CloudFormation Events.
    """
    return

def handler(event, context):

    # update the logger with event info
    global logger
    logger = crhelper.log_config(event)
    return crhelper.cfn_handler(event, context, create, update, delete, logger,
                                init_failed)

def get_ubuntu_releases():
    ubuntu_releases = {}
    r = requests.get('http://releases.ubuntu.com/')
    regex = re.compile(r'\bUbuntu [0-9].*\)')

    result = set(regex.findall(r.text))

    for rel in sorted(result):
        r = re.search(r'(.*(?=\())\((.*\w.*)\)',rel)
        version = r.group(1).replace('Ubuntu', '').replace('LTS','').replace('Beta', '')
        version = ''.join(version.split())
        if len(version) > 5:
            version = version[:-2]

        ubuntu_releases[version] = r.group(2).split(' ')[0].lower()
        if version[-2:] == '04':
            ubuntu_releases[version[:2]] = r.group(2).split(' ')[0].lower()

    return ubuntu_releases

def get_ami(ami_type, ami_version=None):
    ssm_lookup_types = [ 'amzn','amzn2', 'ecs','ecs-arm64', 'ecs-amzn', 'ecs-gpu' ]
    filter_string = None

    if ami_type == 'rhel':
        if ami_version == None:
            ami_version = '7.6'
        filter_string = "RHEL-{}_HVM_GA-*-x86_64-*-Hourly2-GP2".format(ami_version)
        owner_account = '309956199498'
    elif ami_type == 'ubuntu':
        ubuntu_labels = get_ubuntu_releases()

        if ami_version == None:
            ami_version = '18.04'
            
        filter_string = "ubuntu/images/hvm-ssd/ubuntu-{}-{}-amd64-server-*".format(ubuntu_labels[ami_version], ami_version)
        owner_account = '099720109477'
    elif ami_type == 'sles':
        if ami_version == None:
            ami_version = '15'
        owner_account = '013907871322'
        filter_string = 'suse-sles-{}'.format(ami_version)

    if filter_string and 'ami_type' not in ssm_lookup_types:
        ec2_client = boto3.client('ec2')

        ami_search = ec2_client.describe_images(
            Owners=[owner_account],
            Filters=[
                {
                    'Name': 'name',
                    'Values': [
                        filter_string,
                    ]
                },
            ]
        )

        ami_list = []
        for ami in ami_search['Images']:
            ami_list.append((ami['ImageId'], ami['CreationDate']))

        return sorted(ami_list, key=lambda create_date: create_date[1], reverse=True)[0][0]
    else:
        ssm_client = boto3.client('ssm')

        ssm_ps_base_path = '/aws/service'

        if ami_version is None and ami_type == 'windows':
            ami_version = '2019'            

        ssm_ps_service_path = {
            'amzn': '/ami-amazon-linux-latest/amzn-ami-hvm-x86_64-gp2',
            'amzn2': '/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2',
            'ecs': '/ecs/optimized-ami/amazon-linux-2/recommended',
            'ecs-amzn': '/ecs/optimized-ami/amazon-linux/recommended',
            'ecs-arm64': '/ecs/optimized-ami/amazon-linux-2/arm64/recommended',
            'ecs-gpu': '/ecs/optimized-ami/amazon-linux-2/gpu/recommended',
            'windows': '/ami-windows-latest/Windows_Server-{}-English-Full-Base'.format(ami_version)
        }

        if 'amzn' in ami_type and ami_version:
            ami_type = ami_type + ami_version
        elif 'ecs' in ami_type and ami_version:
            ami_type = ami_type + ami_version

        try:
            response = ssm_client.get_parameter(
                Name=ssm_ps_base_path + ssm_ps_service_path[ami_type]
            )
        except Exception as e:
            print(e)
            return None

        return response['Parameter']['Value']
