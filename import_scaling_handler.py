from __future__ import print_function

import boto3
import os
import json
import urllib.request
import urllib.error

asg_client = boto3.client('autoscaling')


def ensure_running(asg_name):
    print('Setting desired capacity of %s to 1' % asg_name)
    asg_client.set_desired_capacity(
        AutoScalingGroupName=asg_name,
        DesiredCapacity=1,
        HonorCooldown=False
    )


def ensure_notrunning(asg_name):
    print('Setting desired capacity of %s to 0' % asg_name)
    asg_client.set_desired_capacity(
        AutoScalingGroupName=asg_name,
        DesiredCapacity=0,
        HonorCooldown=True
    )

def is_import_needed(check_endpoint):
    request = urllib.request.Request(
        url=check_endpoint,
        headers={'Accept': 'application/json'}
    )

    try:
        with urllib.request.urlopen(request) as response:
            content = response.read().decode('utf-8').strip().lower()

            print('Import check API endpoint "%s" returned: [%d %s] %s' % (
                check_endpoint,
                response.status,
                response.msg,
                content
            ))

            return content == 'true'
    except urllib.error.HTTPError as error:
        print('Import check API endpoint "%s" has failed: [%d %s] %s' % (
                check_endpoint,
                error.code,
                error.msg,
                error.read().decode('utf-8')
            ))

        raise error

def handle(event, context):
    asg_name = os.environ['ASG_NAME']
    check_endpoint = os.environ['CHECK_ENDPOINT']

    # There's no downside in doing the calls everytime,
    # if we'd like to check current ASG status that's additional call anyway
    # not worth it
    if is_import_needed(check_endpoint):
        print('Import instance needed')
        ensure_running(asg_name)
    else:
        print('Import not needed')
        ensure_notrunning(asg_name)
