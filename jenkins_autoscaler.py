#!/usr/bin/env python3
import os
import boto3
import ast
import time
import json
import requests


def put_cw_metrics(master, username, password, url):
    """Poll Jenkins API for number of busy/idle executors."""

    dimensions = [{"Name": "JenkinsMaster", "Value": master}]
    cloudwatch = boto3.client('cloudwatch')
    r = requests.get("{}/computer/api/json".format(url), auth=(username, password))
    computer_info = r.json()
    available = computer_info["totalExecutors"] - computer_info["busyExecutors"]
    print(json.dumps({"message": "got number of executors", "available": available, "busy": computer_info["busyExecutors"]}))
    response = cloudwatch.put_metric_data(
        Namespace='Jenkins',
        MetricData=[
            {
                "MetricName": "FreeExecutors",
                "Dimensions": dimensions,
                "Value": available
            },
            {
                "MetricName": "BusyExecutors",
                "Dimensions": dimensions,
                "Value": computer_info["busyExecutors"]
            },
            {
                "MetricName": "TotalExecutors",
                "Dimensions": dimensions,
                "Value": computer_info["totalExecutors"]
            }
        ]
    )

def protect_busy_nodes(username, password, url):
    """Polls Jenkins for idle nodes. Sets scale-in protection on those that aren't idle, and removes it from those that are."""

    global was_building  # global because we are using it to persist the state of nodes across separate function calls
    # normal Jenkins API doesn't work https://bugs.launchpad.net/python-jenkins/+bug/1787430
    response = requests.get("{}/computer/api/json?tree=computer[idle,displayName]".format(url), auth=(username, password)).json()
    nodes = [node for node in response['computer'] if node['displayName'] != 'master']
    for node in nodes:
        idle = node['idle']
        if not idle:
            print(json.dumps({"message": "node is building", "node": node['displayName']}))
            if was_building.get(node['displayName'], False) == False:
                print(json.dumps({"message": "protecting node", "node": node['displayName']}))
                set_protection_from_displayname(node['displayName'], True)
            was_building[node['displayName']] = True
        else:
            print(json.dumps({"message": "node is not building", "node": node['displayName']}))
            if was_building.get(node['displayName'], False) == True:
                print(json.dumps({"message": "unprotecting node", "node": node['displayName']}))
                set_protection_from_displayname(node['displayName'], False)
            was_building[node['displayName']] = False


def set_protection_from_displayname(displayname, is_protected):
    """Sets scale-in protection from a given display name i.e. `ip-10-212-11-36.ap-southeast-2.compute.internal-57934174`"""

    fdqn = ""
    hostname = ""
    instance = {}

    asg = boto3.client('autoscaling')
    ec2 = boto3.client('ec2')
    fqdn = displayname.rsplit('-', 1)[0]  # Jenkins adds some string like `-23452345` to the hostname
    hostname = fqdn.split('.', 1)[0]  # search domains configured on the host may result in a different FDQN for that host than the AWS private DNS name e.g. `ip-10-77-33-147.example`
    filters = [{"Name": "private-dns-name", "Values": [hostname + '*']}]
    try:
        instance = ec2.describe_instances(Filters=filters)['Reservations'][0]['Instances'][0]
    except IndexError:
        print(json.dumps({"message": "could not find instance".format(region), "node": displayname, "fdqn": fqdn, "hostname": hostname, "instance": instance}))
    id = instance['InstanceId']
    asg_name = [x for x in instance['Tags'] if x['Key'] == 'aws:autoscaling:groupName'][0]['Value']
    asg.set_instance_protection(InstanceIds=[id], AutoScalingGroupName=asg_name, ProtectedFromScaleIn=is_protected)


def set_region():
    """Helper function for setting region if it's not explicitly provided."""

    region = None
    session = boto3.session.Session()
    region = session.region_name
    if region:  # already defined in env var or config file
        return
    else:
        try:
            region = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document").json()['region']
            boto3.setup_default_session(region_name=region)
            print(json.dumps({"message": "set region to {}".format(region)}))
        except:
            print(json.dumps({"message": "getting region failed from instance metadata failed"}))
            pass


if __name__ == "__main__":
    master   = os.environ['JENKINS_METRICS_MASTER']
    username = os.environ['JENKINS_METRICS_USERNAME']
    password = os.environ['JENKINS_METRICS_PASSWORD']
    url      = os.environ.get('JENKINS_METRICS_URL', 'http://localhost:8080')
    print(json.dumps({"message": "starting jenkins_autoscaler", "JenkinsMaster": master, 'url': url}))
    set_region()
    global was_building
    was_building = {}
    while True:
        put_cw_metrics(master=master, username=username, password=password, url=url)
        protect_busy_nodes(username=username, password=password, url=url)
        time.sleep(10)
