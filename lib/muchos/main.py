#!/usr/bin/env python3

# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Script to help deploy a Fluo or Accumulo cluster (optionally to AWS EC2)
"""

import os
import sys
from sys import exit
import shutil
from botocore.exceptions import ClientError
from .config import DeployConfig, HOST_VAR_DEFAULTS, PLAY_VAR_DEFAULTS
from .util import parse_args, AMI_HELP_MSG, get_block_device_map
from os.path import isfile, join
import time
import subprocess
import boto3


class MuchosCluster:

    def __init__(self, config):
        self.config = config

    def launch_node(self, hostname, services, sg_id):

        associate_public_ip = True
        if self.config.has_option('ec2', 'associate_public_ip'):
            associate_public_ip = self.config.get('ec2', 'associate_public_ip').strip().lower() == 'true'

        request = {'MinCount': 1, 'MaxCount': 1,
                   'NetworkInterfaces': [{'DeviceIndex': 0, 'AssociatePublicIpAddress': associate_public_ip,
                                          'Groups': [sg_id]}]}

        if self.config.has_option('ec2', 'subnet_id'):
            request['NetworkInterfaces'][0]['SubnetId'] = self.config.get('ec2', 'subnet_id')

        if 'worker' in services:
            instance_type = self.config.get('ec2', 'worker_instance_type')
        else:
            instance_type = self.config.get('ec2', 'default_instance_type')
        request['InstanceType'] = instance_type
        request['InstanceInitiatedShutdownBehavior'] = self.config.get('ec2', 'shutdown_behavior')

        if not self.config.has_option('ec2', 'aws_ami'):
            exit('aws_ami property must be set!')
        image_id = self.config.get('ec2', 'aws_ami')
        if not image_id:
            exit('aws_ami property was not properly')

        request['ImageId'] = image_id
        request['BlockDeviceMappings'] = get_block_device_map(instance_type)

        if self.config.has_option('ec2', 'key_name'):
            request['KeyName'] = self.config.get('ec2', 'key_name')

        tags = [{'Key': 'Name', 'Value': self.config.cluster_name + '-' + hostname},
                {'Key': 'Muchos', 'Value': self.config.cluster_name}]
        for key, val in self.config.instance_tags().items():
            tags.append({'Key': key, 'Value': val})
        request['TagSpecifications'] = [{'ResourceType': 'instance', 'Tags': tags}]

        if self.config.has_option('ec2', 'user_data_path'):
            user_data_path = self.config.get('ec2', 'user_data_path')
            with open(user_data_path, 'r') as user_data_file:
                user_data = user_data_file.read()
            request['UserData'] = user_data

        ec2 = boto3.client('ec2')
        response = None
        try:
            response = ec2.run_instances(**request)
        except ClientError as e:
            exit("ERROR - Failed to launch EC2 instance due to exception:\n\n{0}\n\n{1}".format(e, AMI_HELP_MSG))

        if response is None or len(response['Instances']) != 1:
            exit('ERROR - Failed to start {0} node'.format(hostname))

        print('Launching {0} node using {1}'.format(hostname, image_id))
        return response['Instances'][0]

    def create_security_group(self):
        ec2 = boto3.client('ec2')
        sg = self.config.sg_name
        create_group = True
        group_id = None
        try:
            response = ec2.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': [sg]}])
            if len(response['SecurityGroups']) > 0:
                group_id = response['SecurityGroups'][0]['GroupId']
                create_group = False
        except ClientError:
            pass

        if create_group:
            print("Creating security group " + sg)
            request = {'Description': "Security group created by Muchos", 'GroupName': sg}
            if self.config.has_option('ec2', 'vpc_id'):
                request['VpcId'] = self.config.get('ec2', 'vpc_id')
            response = ec2.create_security_group(**request)
            group_id = response['GroupId']
            ec2.authorize_security_group_ingress(GroupName=sg, SourceSecurityGroupName=sg)
            ec2.authorize_security_group_ingress(GroupName=sg, IpProtocol='tcp', FromPort=22, ToPort=22,
                                                 CidrIp='0.0.0.0/0')
        return group_id

    def delete_security_group(self):
        sg_id = None
        ec2 = boto3.client('ec2')
        try:
            response = ec2.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': [self.config.sg_name]}])
            if len(response['SecurityGroups']) > 0:
                sg_id = response['SecurityGroups'][0]['GroupId']
        except ClientError:
            pass

        if not sg_id:
            print("Could not find security group '{0}'".format(self.config.sg_name))
            return

        print("Attempting to delete security group '{0}' with id '{1}'...".format(self.config.sg_name, sg_id))
        sg_exists = True
        while sg_exists:
            try:
                request = {'GroupId': sg_id}
                ec2.delete_security_group(**request)
                sg_exists = False
            except ClientError as e:
                print("Failed to delete security group '{0}' due exception below:\n{1}\nRetrying in 10 sec..."\
                    .format(self.config.sg_name, e))
                time.sleep(10)
        print("Deleted security group")

    def launch(self):
        if self.active_nodes():
            exit('ERROR - There are already instances running for {0} cluster'.format(self.config.cluster_name))

        if isfile(self.config.hosts_path):
            exit("ERROR - A hosts file already exists at {0}.  Please delete before running launch again"
                 .format(self.config.hosts_path))

        self.config.verify_launch()

        print("Launching {0} cluster".format(self.config.cluster_name))

        if self.config.has_option('ec2', 'security_group_id'):
            sg_id = self.config.get('ec2', 'security_group_id')
        else:
            sg_id = self.create_security_group()

        instance_d = {}
        for (hostname, services) in list(self.config.nodes().items()):
            instance = self.launch_node(hostname, services, sg_id)
            instance_d[instance['InstanceId']] = hostname

        num_running = len(self.status(['running']))
        num_expected = len(self.config.nodes())
        while num_running != num_expected:
            print("{0} of {1} nodes have started.  Waiting another 5 sec..".format(num_running, num_expected))
            time.sleep(5)
            num_running = len(self.status(['running']))

        with open(self.config.hosts_path, 'w') as hosts_file:
            for instance in self.status(['running']):
                public_ip = ''
                if 'PublicIpAddress' in instance:
                    public_ip = instance['PublicIpAddress']
                private_ip = instance['PrivateIpAddress']
                hostname = instance_d[instance['InstanceId']]
                print(hostname, private_ip, public_ip, file=hosts_file)

        print("All {0} nodes have started. Created hosts file at {1}".format(num_expected, self.config.hosts_path))

    def sync(self):
        config = self.config
        print('Syncing ansible directory on {0} cluster proxy node'.format(config.cluster_name))

        host_vars = HOST_VAR_DEFAULTS
        play_vars = PLAY_VAR_DEFAULTS

        for section in ("general", "ansible-vars", config.get('performance', 'profile')):
            for (name, value) in config.items(section):
                if name not in ('proxy_hostname', 'proxy_socks_port'):
                    if name in host_vars:
                        host_vars[name] = value
                    if name in play_vars:
                        play_vars[name] = value

        play_vars['accumulo_sha256'] = config.checksum('accumulo')
        play_vars['fluo_sha256'] = config.checksum('fluo')
        play_vars['fluo_yarn_sha256'] = config.checksum('fluo_yarn')
        play_vars['hadoop_sha256'] = config.checksum('hadoop')
        play_vars['spark_sha256'] = config.checksum('spark')
        play_vars['zookeeper_sha256'] = config.checksum('zookeeper')

        cloud_provider = host_vars.get('cloud_provider', 'ec2')
        node_type_map = {}
        if cloud_provider == 'ec2':
            node_type_map = config.node_type_map()
            play_vars["mount_root"] = config.mount_root
            play_vars["metrics_drive_ids"] = config.metrics_drive_ids()
            play_vars["fstype"] = config.fstype()
            play_vars["force_format"] = config.force_format()
            play_vars["shutdown_delay_minutes"] = config.get("ec2", "shutdown_delay_minutes")
        if cloud_provider == 'baremetal':
            play_vars["mount_root"] = config.get("baremetal", "mount_root")
            play_vars["metrics_drive_ids"] = config.get("baremetal", "metrics_drives_ids").split(",")
            mounts = config.get("baremetal", "mounts").split(",")
            devices = config.get("baremetal", "devices").split(",")
            for node_type in 'default', 'worker':
                node_type_map[node_type] = {'mounts': mounts, 'devices': devices}

        play_vars["node_type_map"] = node_type_map
        host_vars['worker_data_dirs'] = str(node_type_map['worker']['mounts'])
        host_vars['default_data_dirs'] = str(node_type_map['default']['mounts'])

        with open(join(config.deploy_path, "ansible/site.yml"), 'w') as site_file:
            print("- import_playbook: common.yml", file=site_file)
            if config.has_service("spark"):
                print("- import_playbook: spark.yml", file=site_file)
            print("- import_playbook: hadoop.yml", file=site_file)
            print("- import_playbook: zookeeper.yml", file=site_file)
            if config.has_service("metrics"):
                print("- import_playbook: metrics.yml", file=site_file)
            print("- import_playbook: accumulo.yml", file=site_file)
            if config.has_service('fluo'):
                print("- import_playbook: fluo.yml", file=site_file)
            if config.has_service('fluo_yarn'):
                print("- import_playbook: fluo_yarn.yml", file=site_file)
            if config.has_service("mesosmaster"):
                print("- import_playbook: mesos.yml", file=site_file)
            if config.has_service("swarmmanager"):
                print("- import_playbook: docker.yml", file=site_file)

        ansible_conf = join(config.deploy_path, "ansible/conf")
        with open(join(ansible_conf, "hosts"), 'w') as hosts_file:
            print("[proxy]\n{0}".format(config.proxy_hostname()), file=hosts_file)
            print("\n[accumulomaster]\n{0}".format(config.get_service_hostnames("accumulomaster")[0]), file=hosts_file)
            print("\n[namenode]\n{0}".format(config.get_service_hostnames("namenode")[0]), file=hosts_file)
            print("\n[resourcemanager]\n{0}".format(config.get_service_hostnames("resourcemanager")[0]), file=hosts_file)
            if config.has_service("spark"):
                print("\n[spark]\n{0}".format(config.get_service_hostnames("spark")[0]), file=hosts_file)
            if config.has_service("mesosmaster"):
                print("\n[mesosmaster]\n{0}".format(config.get_service_hostnames("mesosmaster")[0]), file=hosts_file)
            if config.has_service("metrics"):
                print("\n[metrics]\n{0}".format(config.get_service_hostnames("metrics")[0]), file=hosts_file)
            if config.has_service("swarmmanager"):
                print("\n[swarmmanager]\n{0}".format(config.get_service_hostnames("swarmmanager")[0]), file=hosts_file)

            print("\n[zookeepers]", file=hosts_file)
            for (index, zk_host) in enumerate(config.get_service_hostnames("zookeeper"), start=1):
                print("{0} id={1}".format(zk_host, index), file=hosts_file)

            if config.has_service('fluo'):
                print("\n[fluo]", file=hosts_file)
                for host in config.get_service_hostnames("fluo"):
                    print(host, file=hosts_file)

            if config.has_service('fluo_yarn'):
                print("\n[fluo_yarn]", file=hosts_file)
                for host in config.get_service_hostnames("fluo_yarn"):
                    print(host, file=hosts_file)

            print("\n[workers]", file=hosts_file)
            for worker_host in config.get_service_hostnames("worker"):
                print(worker_host, file=hosts_file)

            print("\n[accumulo:children]\naccumulomaster\nworkers", file=hosts_file)
            print("\n[hadoop:children]\nnamenode\nresourcemanager\nworkers", file=hosts_file)

            print("\n[nodes]", file=hosts_file)
            for (private_ip, hostname) in config.get_private_ip_hostnames():
                print("{0} ansible_ssh_host={1} node_type={2}".format(hostname, private_ip,
                                                                                    config.node_type(hostname)), file=hosts_file)

            print("\n[all:vars]", file=hosts_file)
            for (name, value) in sorted(host_vars.items()):
                print("{0} = {1}".format(name, value), file=hosts_file)

        with open(join(config.deploy_path, "ansible/group_vars/all"), 'w') as play_vars_file:
            for (name, value) in sorted(play_vars.items()):
                print("{0}: {1}".format(name, value), file=play_vars_file)

        # copy keys file to ansible/conf (if it exists)
        conf_keys = join(config.deploy_path, "conf/keys")
        ansible_keys = join(ansible_conf, "keys")
        if isfile(conf_keys):
            shutil.copyfile(conf_keys, ansible_keys)
        else:
            open(ansible_keys, 'w').close()

        basedir = config.get('general', 'cluster_basedir')
        cmd = "rsync -az --delete -e \"ssh -o 'StrictHostKeyChecking no'\""
        subprocess.call("{cmd} {src} {usr}@{ldr}:{tdir}".format(cmd=cmd, src=join(config.deploy_path, "ansible"),
                        usr=config.get('general', 'cluster_user'), ldr=config.get_proxy_ip(), tdir=basedir),
                        shell=True)

        self.exec_on_proxy_verified("{0}/ansible/scripts/install_ansible.sh".format(basedir), opts='-t')

    def setup(self):
        config = self.config
        print('Setting up {0} cluster'.format(config.cluster_name))

        self.sync()

        conf_upload = join(config.deploy_path, "conf/upload")
        accumulo_tarball = join(conf_upload, "accumulo-{0}-bin.tar.gz".format(config.version("accumulo")))
        fluo_tarball = join(conf_upload, "fluo-{0}-bin.tar.gz".format(config.version("fluo")))
        fluo_yarn_tarball = join(conf_upload, "fluo-yarn-{0}-bin.tar.gz".format(config.version("fluo_yarn")))
        basedir = config.get('general', 'cluster_basedir')
        cluster_tarballs = "{0}/tarballs".format(basedir)
        self.exec_on_proxy_verified("mkdir -p {0}".format(cluster_tarballs))
        if isfile(accumulo_tarball):
            self.send_to_proxy(accumulo_tarball, cluster_tarballs)
        if isfile(fluo_tarball) and config.has_service('fluo'):
            self.send_to_proxy(fluo_tarball, cluster_tarballs)
        if isfile(fluo_yarn_tarball) and config.has_service('fluo_yarn'):
            self.send_to_proxy(fluo_yarn_tarball, cluster_tarballs)

        self.execute_playbook("site.yml")

    def status(self, states):
        ec2 = boto3.client('ec2')
        response = ec2.describe_instances(Filters=[{'Name': 'tag:Muchos', 'Values': [self.config.cluster_name]}])
        nodes = []
        for res in response['Reservations']:
            for inst in res['Instances']:
                if inst['State']['Name'] in states:
                    nodes.append(inst)
        return nodes

    def active_nodes(self):
        return self.status(['pending', 'running', 'stopping', 'stopped'])

    @staticmethod
    def print_nodes(nodes):
        for node in nodes:
            name = 'Unknown'
            for tag in node['Tags']:
                if tag['Key'] == 'Name':
                    name = tag['Value']
            print("  ", name, node['InstanceId'], node['PrivateIpAddress'], node.get('PublicIpAddress', ''))

    def terminate(self, hosts_path):
        nodes = self.active_nodes()
        print("The following {0} nodes in {1} cluster will be terminated:".format(len(nodes), self.config.cluster_name))
        self.print_nodes(nodes)

        response = input("Do you want to continue? (y/n) ")
        if response == "y":
            ec2 = boto3.client('ec2')
            for node in nodes:
                ec2.terminate_instances(InstanceIds=[node['InstanceId']])

            print("Terminated nodes.")
            if not self.config.has_option('ec2', 'security_group_id'):
                self.delete_security_group()

            if isfile(hosts_path):
                os.remove(hosts_path)
                print("Removed hosts file at ", hosts_path)
        else:
            print("Aborted termination")

    def ssh(self):
        self.wait_until_proxy_ready()
        fwd = ''
        if self.config.has_option('general', 'proxy_socks_port'):
            fwd = "-D " + self.config.get('general', 'proxy_socks_port')
        ssh_command = "ssh -C -A -o 'StrictHostKeyChecking no' {fwd} {usr}@{ldr}".format(
            usr=self.config.get('general', 'cluster_user'), ldr=self.config.get_proxy_ip(), fwd=fwd)
        print("Logging into proxy using: {0}".format(ssh_command))
        retcode = subprocess.call(ssh_command, shell=True)
        if retcode != 0:
            exit("ERROR - Command failed with return code of {0}: {1}".format(retcode, ssh_command))

    def exec_on_proxy(self, command, opts=''):
        ssh_command = "ssh -A -o 'StrictHostKeyChecking no' {opts} {usr}@{ldr} '{cmd}'".format(
                usr=self.config.get('general', 'cluster_user'),
                ldr=self.config.get_proxy_ip(), cmd=command, opts=opts)
        return subprocess.call(ssh_command, shell=True), ssh_command

    def exec_on_proxy_verified(self, command, opts=''):
        (retcode, ssh_command) = self.exec_on_proxy(command, opts)
        if retcode != 0:
            exit("ERROR - Command failed with return code of {0}: {1}".format(retcode, ssh_command))

    def wait_until_proxy_ready(self):
        cluster_user = self.config.get('general', 'cluster_user')
        print("Checking if '{0}' proxy can be reached using: ssh {1}@{2}"\
            .format(self.config.proxy_hostname(), cluster_user, self.config.get_proxy_ip()))
        while True:
            (retcode, ssh_command) = self.exec_on_proxy('pwd > /dev/null')
            if retcode == 0:
                print("Connected to proxy using SSH!")
                time.sleep(1)
                break
            print("Proxy could not be accessed using SSH.  Will retry in 5 sec...")
            time.sleep(5)

    def execute_playbook(self, playbook):
        print("Executing '{0}' playbook".format(playbook))
        basedir = self.config.get('general', 'cluster_basedir')
        self.exec_on_proxy_verified("time -p ansible-playbook {base}/ansible/{playbook}"
                                    .format(base=basedir, playbook=playbook), opts='-t')

    def send_to_proxy(self, path, target, skip_if_exists=True):
        print("Copying to proxy: ", path)
        cmd = "scp -o 'StrictHostKeyChecking no'"
        if skip_if_exists:
            cmd = "rsync --update --progress -e \"ssh -o 'StrictHostKeyChecking no'\""
        subprocess.call("{cmd} {src} {usr}@{ldr}:{tdir}".format(
            cmd=cmd, src=path, usr=self.config.get('general', 'cluster_user'), ldr=self.config.get_proxy_ip(),
            tdir=target), shell=True)


def main():
    deploy_path = os.environ.get('MUCHOS_HOME')
    if not deploy_path:
        exit('ERROR - MUCHOS_HOME env variable must be set!')
    if not os.path.isdir(deploy_path):
        exit('ERROR - Directory set by MUCHOS_HOME does not exist: '+deploy_path)

    config_path = join(deploy_path, "conf/muchos.props")
    if not isfile(config_path):
        exit('ERROR - A config file does not exist at '+config_path)
    checksums_path = join(deploy_path, "conf/checksums")
    if not isfile(checksums_path):
        exit('ERROR - A checksums file does not exist at '+checksums_path)

    hosts_dir = join(deploy_path, "conf/hosts/")

    # parse command line args
    retval = parse_args(hosts_dir)
    if not retval:
        print("Invalid command line arguments. For help, use 'muchos -h'")
        sys.exit(1)
    (opts, action, args) = retval

    hosts_path = join(hosts_dir, opts.cluster)

    config = DeployConfig(deploy_path, config_path, hosts_path, checksums_path, opts.cluster)
    config.verify_config(action)

    cluster = MuchosCluster(config)

    if action == 'launch':
        cluster.launch()
    elif action == 'status':
        nodes = cluster.status(['running'])
        print("Found {0} nodes in {1} cluster".format(len(nodes), config.cluster_name))
        cluster.print_nodes(nodes)
    elif action == 'sync':
        cluster.sync()
    elif action == 'setup':
        cluster.setup()
    elif action == 'config':
        if opts.property == 'all':
            config.print_all()
        else:
            config.print_property(opts.property)
    elif action == 'ssh':
        cluster.ssh()
    elif action in ('wipe', 'kill', 'cancel_shutdown'):
        if not isfile(hosts_path):
            exit("Hosts file does not exist for cluster: "+hosts_path)
        if action == 'wipe':
            print("Killing all processes started by Muchos and wiping Muchos data from {0} cluster"\
                .format(config.cluster_name))
        elif action == 'kill':
            print("Killing all processes started by Muchos on {0} cluster".format(config.cluster_name))
        elif action == 'cancel_shutdown':
            print("Cancelling automatic shutdown of {0} cluster".format(config.cluster_name))
        cluster.execute_playbook(action + ".yml")
    elif action == 'terminate':
        cluster.terminate(hosts_path)
    else:
        print('ERROR - Unknown action:', action)


main()
