from __future__ import print_function

import boto3
import os
import json
import paramiko
import jinja2
from io import StringIO

from datetime import datetime

def execute_command(ssh_client, command):
    print('Executing %s' % command)
    stdin, stdout, stderr = ssh_client.exec_command(command)
    print(stdout.read(), stderr.read())


def handle(event, context):
    ssh_key = event['varnish_ssh_key']
    ssh_username = event['varnish_ssh_username']
    varnish_hosts = event['varnish_hosts']
    backend_hosts = event['backend_hosts']
    extra_hosts = event['extra_hosts']
    timestamp = datetime.now().strftime('%Y-%m-%d.%H-%M-%S.%f')
    new_vcl_name = 'new-backends-%s.vcl' % timestamp

    backend_template = json.loads(os.environ['BACKEND_TEMPLATE'])
    backend_template_vars = json.loads(os.environ['BACKEND_TEMPLATE_VARS'])
    backend_template_vars['varnish_backend_instances_app'] = [{'private_ip_address': ip, 'instance_id': 'app' + ip.replace('.', '')} for ip in backend_hosts]
    backend_template_vars['varnish_backend_instances_extra'] = [{'private_ip_address': ip, 'instance_id': 'ext' + ip.replace('.', '')} for ip in extra_hosts]
    backend_vcl = jinja2.Environment(loader=jinja2.BaseLoader).from_string(backend_template).render(**backend_template_vars)

    ssh_key = paramiko.RSAKey.from_private_key(StringIO.StringIO(ssh_key))

    for host in varnish_hosts:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        print('Connecting to %s...' % host)
        ssh_client.connect(hostname = host, username = ssh_username, pkey = ssh_key)

        print('Copying new backends vcl to %s ...' % new_vcl_name)
        sftp = ssh_client.open_sftp()
        sftp.putfo(StringIO.StringIO(backend_vcl), new_vcl_name)

        print('Updating vcls...')
        execute_command(ssh_client, 'sudo /usr/bin/varnish_update_backends %s' % new_vcl_name)

        ssh_client.close()






















