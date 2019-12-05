from __future__ import print_function

import boto3
import os
import json

LIFECYCLE_ACTION_CONTINUE = 'CONTINUE'
LIFECYCLE_ACTION_ABANDON = 'ABANDON'

LAUNCH_SUCCESSFUL_EVENT = 'EC2 Instance Launch Successful'

KEY_LIFECYCLE = 'LifecycleHookName'
KEY_EC2_INSTANCE_ID = 'EC2InstanceId'
KEY_ASG_NAME = 'AutoScalingGroupName'


def get_ec2_hosts(instance_filter, exclude_instance_ids=None):
    if exclude_instance_ids is None:
        exclude_instance_ids = []

    ec2_client = boto3.client('ec2')
    reservations = ec2_client.describe_instances(Filters=instance_filter)['Reservations']

    hosts = []

    for reservation in reservations:
        for instance in reservation['Instances']:
            if not instance['State']['Name'] == 'running' or instance['InstanceId'] in exclude_instance_ids:
                continue

            hosts.append(instance['PrivateIpAddress'])

    return hosts


def update_backends(exclude_backend_instance_ids=None, wait_for_finish=False):
    backend_instance_filter = json.loads(os.environ['BACKEND_INSTANCE_FILTER'])
    extra_instance_filter = json.loads(os.environ['EXTRA_INSTANCE_FILTER'])
    varnish_instance_filter = json.loads(os.environ['VARNISH_INSTANCE_FILTER'])
    varnish_key_bucket = os.environ['KEY_BUCKET']
    varnish_key_name = os.environ['KEY_NAME']
    varnish_ssh_username = os.environ['SSH_USERNAME']
    update_lambda_name = os.environ['UPDATE_LAMBDA_NAME']

    if exclude_backend_instance_ids:
        print("Ignoring backend instances %s" % ', '.join(exclude_backend_instance_ids))

    varnish_hosts = get_ec2_hosts(varnish_instance_filter)
    backend_hosts = get_ec2_hosts(backend_instance_filter, exclude_backend_instance_ids)
    extra_hosts = get_ec2_hosts(extra_instance_filter, exclude_backend_instance_ids)

    print("Varnish hosts to be updated: %s, found using filter %s" % (varnish_hosts, varnish_instance_filter))
    print("New backend hosts: %s, found using filter %s" % (backend_hosts, backend_instance_filter))
    print("New extra hosts: %s, found using filter %s" % (extra_hosts, extra_instance_filter))

    s3_client = boto3.client('s3')
    varnish_key_object = s3_client.get_object(Bucket=varnish_key_bucket, Key=varnish_key_name)
    varnish_key = varnish_key_object['Body'].read()

    print("Downloaded varnish ssh key from %s/%s" % (varnish_key_bucket, varnish_key_name))

    payload = json.dumps({
        'varnish_ssh_key': varnish_key,
        'varnish_ssh_username': varnish_ssh_username,
        'varnish_hosts': varnish_hosts,
        'backend_hosts': backend_hosts,
        'extra_hosts': extra_hosts,
    })

    if wait_for_finish:
        print('Invoking update lambda with wait')
        invocation_type = 'RequestResponse'
    else:
        print('Invoking update lambda asynchronously')
        invocation_type = 'Event'

    boto3.client('lambda').invoke(
        FunctionName=update_lambda_name,
        InvocationType=invocation_type,
        LogType='Tail',
        Payload=payload
    )

    if wait_for_finish:
        print('Update lambda finished')


def complete_lifecycle_action(hook, asg, instance_id, action=LIFECYCLE_ACTION_CONTINUE):
    asg_client = boto3.client('autoscaling')

    response = asg_client.complete_lifecycle_action(
        LifecycleHookName=hook,
        AutoScalingGroupName=asg,
        LifecycleActionResult=action,
        InstanceId=instance_id
    )

    print("Asg continue response: %s" % response)


def handle_plain_event(event_type, event_data):
    print('Handling plain event "%s"' % event_type)

    if event_type != LAUNCH_SUCCESSFUL_EVENT:
        print('Unsupported event type, doing nothing')
        return

    update_backends()


def handle_lifecycle_event(event_type, event_data):
    terminate_hook = os.environ['TERMINATE_HOOK']
    current_hook = event_data[KEY_LIFECYCLE]
    asg_name = event_data[KEY_ASG_NAME]
    instance_id = event_data[KEY_EC2_INSTANCE_ID]

    print('Handling lifecycle event "%s" / hook "%s"' % (event_type, current_hook))

    if current_hook == terminate_hook:
        update_backends([instance_id], True)
        complete_lifecycle_action(current_hook, asg_name, instance_id, LIFECYCLE_ACTION_CONTINUE)
    else:
        print('Unsupported lifecycle hook, doing nothing')


def handle(event, context):
    event_data = event['detail']
    event_type = event['detail-type']
    supported_asg_prefix = os.environ['ASG_PREFIX']
    event_asg_name = event_data[KEY_ASG_NAME]

    if not event_asg_name.startswith(supported_asg_prefix):
        return 'Event triggered by unsupported ASG "%s", exiting...' % event_asg_name

    if KEY_LIFECYCLE in event_data:
        handle_lifecycle_event(event_type, event_data)
    else:
        handle_plain_event(event_type, event_data)

    return "All good"





















