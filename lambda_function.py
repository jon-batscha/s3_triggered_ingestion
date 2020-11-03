import json
import boto3
import time

def lambda_handler(event, context):

    ###CONFIG
    instance_type = 't2.nano' # eg: t2.nano
    ami_id = 'ami-00178b8a98ead1f2d' # eg: ami-0e8123b02c9fbf08b
    key_name = '' # without .pem suffix
    iam_role = 'Admin' # role name
    script_name = 'sample_script.py'
    ## END CONFIG

    # print(event)
    bucketname = event['Records'][0]['s3']['bucket']['name']
    filename = event['Records'][0]['s3']['object']['key']
    project_name = filename.split('/')[0]
    filename_local = filename.split('/')[-1]
    region = event['Records'][0]['awsRegion']
    
    ec2 = boto3.resource('ec2')
    ssm = boto3.client('ssm')
    s3 = boto3.resource('s3')
    
    # launch instance from ami
    response = ec2.create_instances(
        ImageId=ami_id,
        InstanceType=instance_type,
        KeyName=key_name,
        MaxCount=1,
        MinCount=1,
        IamInstanceProfile={
            'Name':iam_role
        }
        )
        
    new_instance = response[0]
    
    new_instance.wait_until_running()
    
    managed_instances = [instance['InstanceId'] for instance in ssm.describe_instance_information()['InstanceInformationList']]
    
    while new_instance.instance_id not in managed_instances:
        
        time.sleep(1)
        managed_instances = [instance['InstanceId'] for instance in ssm.describe_instance_information()['InstanceInformationList']]


    copy_scripts = 'aws s3 cp s3://{bucketname}/{project_name}/scripts/ . --recursive'.format(bucketname=bucketname, project_name=project_name)
    copy_data = 'aws s3 cp s3://{bucketname}/{filename} {filename_local}'.format(bucketname=bucketname, filename=filename, filename_local=filename_local)
    activate_venv = 'source env/bin/activate'
    process_data = 'nohup python {script_name} {filename_local}'.format(script_name=script_name, filename_local=filename_local)
    delete_obj = 'aws s3 rm s3://{bucketname}/{filename}'.format(bucketname=bucketname, filename=filename)
    terminate_instance = 'aws ec2 terminate-instances --region {region} --instance-ids {instance_id}'.format(region=region, instance_id=new_instance.instance_id)
    
    
    ssm.send_command(
        InstanceIds=[new_instance.instance_id],
        DocumentName='AWS-RunShellScript',
        Parameters={
            'commands':[copy_scripts,copy_data,activate_venv,process_data,delete_obj,terminate_instance],
            'workingDirectory':['/home/ec2-user/']
            }
        )

    return {
        'statusCode': 200,
        'body': json.dumps('Done'),
    }
