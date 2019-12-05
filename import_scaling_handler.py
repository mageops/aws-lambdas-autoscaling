from __future__ import print_function

import boto3
import os
import json
import urllib2

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
    request = urllib2.Request(
        url=check_endpoint,
        headers={'Accept': 'application/json'}
    )

    return urllib2.urlopen(request).read().strip().lower() == 'true'


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
