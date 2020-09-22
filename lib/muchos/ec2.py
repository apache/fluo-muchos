#!/usr/bin/env python3
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
from sys import exit
from botocore.exceptions import ClientError
from .util import AMI_HELP_MSG, get_block_device_map
from os import path
import time
import boto3
from .existing import ExistingCluster
import json
from string import Template


class Ec2Cluster(ExistingCluster):
    def __init__(self, config):
        ExistingCluster.__init__(self, config)

    def launch_node(self, hostname, services, sg_id):

        request = self.init_request(hostname, services, sg_id)

        request["MinCount"] = 1
        request["MaxCount"] = 1

        tags = [
            {
                "Key": "Name",
                "Value": self.config.cluster_name + "-" + hostname,
            },
            {"Key": "Muchos", "Value": self.config.cluster_name},
        ]

        for key, val in self.config.instance_tags().items():
            tags.append({"Key": key, "Value": val})

        request["TagSpecifications"] = [
            {"ResourceType": "instance", "Tags": tags}
        ]

        if self.config.has_option("ec2", "user_data_path"):
            user_data_path = self.config.get("ec2", "user_data_path")
            with open(user_data_path, "r") as user_data_file:
                user_data = user_data_file.read()
            request["UserData"] = user_data

        ec2 = boto3.client("ec2")
        response = None
        try:
            response = ec2.run_instances(**request)
        except ClientError as e:
            exit(
                "ERROR - Failed to launch EC2 instance due to exception:"
                "\n\n{0}\n\n{1}".format(e, AMI_HELP_MSG)
            )

        if response is None or len(response["Instances"]) != 1:
            exit("ERROR - Failed to start {0} node".format(hostname))

        print(
            "Launching {0} node using {1}".format(hostname, request["ImageId"])
        )
        return response["Instances"][0]

    def create_security_group(self):
        ec2 = boto3.client("ec2")
        sg = self.config.sg_name
        create_group = True
        group_id = None
        try:
            response = ec2.describe_security_groups(
                Filters=[{"Name": "group-name", "Values": [sg]}]
            )
            if len(response["SecurityGroups"]) > 0:
                group_id = response["SecurityGroups"][0]["GroupId"]
                create_group = False
        except ClientError:
            pass

        if create_group:
            print("Creating security group " + sg)
            request = {
                "Description": "Security group created by Muchos",
                "GroupName": sg,
            }
            if self.config.has_option("ec2", "vpc_id"):
                request["VpcId"] = self.config.get("ec2", "vpc_id")
            response = ec2.create_security_group(**request)
            group_id = response["GroupId"]
            ec2.authorize_security_group_ingress(
                GroupName=sg, SourceSecurityGroupName=sg
            )
            ec2.authorize_security_group_ingress(
                GroupName=sg,
                IpProtocol="tcp",
                FromPort=22,
                ToPort=22,
                CidrIp="0.0.0.0/0",
            )
        return group_id

    def delete_security_group(self):

        sg_id = None
        ec2 = boto3.client("ec2")
        try:
            response = ec2.describe_security_groups(
                Filters=[
                    {"Name": "group-name", "Values": [self.config.sg_name]}
                ]
            )
            if len(response["SecurityGroups"]) > 0:
                sg_id = response["SecurityGroups"][0]["GroupId"]
        except ClientError:
            pass

        if not sg_id:
            print(
                "Could not find security group '{0}'".format(
                    self.config.sg_name
                )
            )
            return

        print(
            "Attempting to delete security group '{0}' "
            "with id '{1}'...".format(self.config.sg_name, sg_id)
        )
        sg_exists = True
        while sg_exists:
            try:
                request = {"GroupId": sg_id}
                ec2.delete_security_group(**request)
                sg_exists = False
            except ClientError as e:
                print(
                    "Failed to delete security group '{0}' due to "
                    "exception below:\n{1}\nRetrying in 10 sec...".format(
                        self.config.sg_name, e
                    )
                )
                time.sleep(10)
        print("Deleted security group")

    def init_request(self, hostname, services, sg_id):
        associate_public_ip = True
        if self.config.has_option("ec2", "associate_public_ip"):
            associate_public_ip = (
                self.config.get("ec2", "associate_public_ip").strip().lower()
                == "true"
            )

        request = {
            "NetworkInterfaces": [
                {
                    "DeviceIndex": 0,
                    "AssociatePublicIpAddress": associate_public_ip,
                    "Groups": [sg_id],
                }
            ]
        }

        if self.config.has_option("ec2", "subnet_id"):
            request["NetworkInterfaces"][0]["SubnetId"] = self.config.get(
                "ec2", "subnet_id"
            )

        if "worker" in services:
            instance_type = self.config.get("ec2", "worker_instance_type")
        else:
            instance_type = self.config.get("ec2", "default_instance_type")
        request["InstanceType"] = instance_type
        request["InstanceInitiatedShutdownBehavior"] = self.config.get(
            "ec2", "shutdown_behavior"
        )

        if not self.config.has_option("ec2", "aws_ami"):
            exit("aws_ami property must be set!")
        image_id = self.config.get("ec2", "aws_ami")
        if not image_id:
            exit("aws_ami property was not properly")

        request["ImageId"] = image_id
        request["BlockDeviceMappings"] = get_block_device_map(instance_type)

        if self.config.has_option("ec2", "key_name"):
            request["KeyName"] = self.config.get("ec2", "key_name")

        return request

    def launch(self):
        if self.active_nodes():
            exit(
                "ERROR - There are already instances "
                "running for {0} cluster".format(self.config.cluster_name)
            )

        if path.isfile(self.config.hosts_path):
            exit(
                "ERROR - A hosts file already exists at {0}. "
                "Please delete before running launch again".format(
                    self.config.hosts_path
                )
            )

        self.config.verify_launch()

        print("Launching {0} cluster".format(self.config.cluster_name))

        if self.config.has_option("ec2", "security_group_id"):
            sg_id = self.config.get("ec2", "security_group_id")
        else:
            sg_id = self.create_security_group()

        instance_d = {}
        for (hostname, services) in list(self.config.nodes().items()):
            instance = self.launch_node(hostname, services, sg_id)
            instance_d[instance["InstanceId"]] = hostname

        num_running = len(self.get_status(["running"]))
        num_expected = len(self.config.nodes())
        while num_running != num_expected:
            print(
                "{0} of {1} nodes have started. "
                "Waiting another 5 sec..".format(num_running, num_expected)
            )
            time.sleep(5)
            num_running = len(self.get_status(["running"]))

        with open(self.config.hosts_path, "w") as hosts_file:
            for instance in self.get_status(["running"]):
                public_ip = ""
                if "PublicIpAddress" in instance:
                    public_ip = instance["PublicIpAddress"]
                private_ip = instance["PrivateIpAddress"]
                hostname = instance_d[instance["InstanceId"]]
                print(
                    "{0} {1} {2}".format(hostname, private_ip, public_ip),
                    file=hosts_file,
                )

        print(
            "All {0} nodes have started. Created hosts file at {1}".format(
                num_expected, self.config.hosts_path
            )
        )

    def status(self):
        nodes = self.get_status(["running"])
        print(
            "Found {0} nodes in {1} cluster".format(
                len(nodes), self.config.cluster_name
            )
        )
        self.print_nodes(nodes)

    def get_status(self, states):
        ec2 = boto3.client("ec2")
        response = ec2.describe_instances(
            Filters=[
                {"Name": "tag:Muchos", "Values": [self.config.cluster_name]}
            ]
        )
        nodes = []
        for res in response["Reservations"]:
            for inst in res["Instances"]:
                if inst["State"]["Name"] in states:
                    nodes.append(inst)
        return nodes

    def active_nodes(self):
        return self.get_status(["pending", "running", "stopping", "stopped"])

    @staticmethod
    def print_nodes(nodes):
        for node in nodes:
            name = "Unknown"
            for tag in node["Tags"]:
                if tag["Key"] == "Name":
                    name = tag["Value"]
            print(
                "  ",
                name,
                node["InstanceId"],
                node["PrivateIpAddress"],
                node.get("PublicIpAddress", ""),
            )

    def stop(self):
        nodes = self.active_nodes()
        print(
            "The following {0} nodes in {1} cluster "
            "will be stopped:".format(len(nodes), self.config.cluster_name)
        )
        ec2 = boto3.client("ec2")
        for node in nodes:
            ec2.stop_instances(InstanceIds=[node["InstanceId"]])
        self.print_nodes(nodes)
        print("Stopped nodes.")

    def start(self):
        nodes = self.active_nodes()
        print(
            "The following {0} nodes in {1} cluster "
            "will be started:".format(len(nodes), self.config.cluster_name)
        )
        ec2 = boto3.client("ec2")
        for node in nodes:
            ec2.start_instances(InstanceIds=[node["InstanceId"]])
        self.print_nodes(nodes)
        print("Started nodes.")

    def terminate(self):
        nodes = self.active_nodes()
        print(
            "The following {0} nodes in {1} cluster "
            "will be terminated:".format(len(nodes), self.config.cluster_name)
        )
        self.print_nodes(nodes)

        response = input("Do you want to continue? (y/n) ")
        if response == "y":
            ec2 = boto3.client("ec2")
            for node in nodes:
                ec2.terminate_instances(InstanceIds=[node["InstanceId"]])

            print("Terminated nodes.")
            if not self.config.has_option("ec2", "security_group_id"):
                self.delete_security_group()

            if path.isfile(self.config.hosts_path):
                os.remove(self.config.hosts_path)
                print("Removed hosts file at ", self.config.hosts_path)
        else:
            print("Aborted termination")

    def wipe(self):
        super().wipe()


class Ec2ClusterTemplate(Ec2Cluster):
    def __init__(self, config):
        Ec2Cluster.__init__(self, config)

    def launch(self):
        print(
            "Using cluster template '{0}' to launch nodes".format(
                self.config.cluster_template_d["id"]
            )
        )
        super().launch()

    def init_request(self, hostname, services, sg_id):
        # the first service in the list denotes the node's target template
        print("Template '{0}' selected for {1}".format(services[0], hostname))
        # interpolate any values from the ec2 config section and create request
        ec2_d = dict(self.config.items("ec2"))
        ec2_d["security_group_id"] = sg_id
        return json.loads(
            Template(self.config.cluster_template_d[services[0]]).substitute(
                ec2_d
            )
        )
