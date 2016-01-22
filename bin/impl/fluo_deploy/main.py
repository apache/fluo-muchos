#!/usr/bin/env python

# Copyright 2014 Fluo authors (see AUTHORS)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Script to help deploy Fluo cluster (optionally to AWS EC2)
"""

import os, sys
import shutil
from config import DeployConfig
from util import setup_boto, parse_args, exit
from os.path import isfile, join
import random
import time
import urllib
import subprocess

FLUO_DEPLOY = os.environ.get('FLUO_DEPLOY')
if FLUO_DEPLOY is None:
  exit('ERROR - The env var FLUO_DEPLOY must be set!')
setup_boto(join(FLUO_DEPLOY, "bin/impl/lib"))

import boto
from boto.ec2.blockdevicemapping import BlockDeviceMapping, BlockDeviceType, EBSBlockDeviceType
from boto import ec2

def get_or_make_group(conn, name, vpc_id):
  groups = conn.get_all_security_groups()
  group = [g for g in groups if g.name == name]
  if len(group) > 0:
    return group[0]
  else:
    print "Creating security group " + name
    return conn.create_security_group(name, "Security group created by fluo-deploy script", vpc_id)

def get_instance(instances, instance_id):
  for instance in instances:
    if instance.id == instance_id:
      return instance

def launch_cluster(conn, config):
  key_name = config.get('ec2', 'key_name')
  if not key_name:
    exit('ERROR - key.name is not set fluo-deploy.props')

  cur_nodes = get_active_cluster(conn, config)
  if cur_nodes:
    exit('ERROR - There are already instances running for {0} cluster'.format(config.cluster_name))

  if isfile(config.hosts_path):
    exit("ERROR - A hosts file already exists at {0}.  Please delete before running launch again".format(config.hosts_path))

  print "Launching {0} cluster".format(config.cluster_name)

  vpc_id = None
  if config.has_option('ec2', 'vpc_id'):
    vpc_id = config.get('ec2', 'vpc_id')

  subnet_id = None
  if config.has_option('ec2', 'subnet_id'):
    subnet_id = config.get('ec2', 'subnet_id')

  security_group = get_or_make_group(conn, config.cluster_name + "-group", vpc_id)
  if security_group.rules == []: # Group was just now created
    if vpc_id is None:
      security_group.authorize(src_group=security_group)
    else:
      security_group.authorize(ip_protocol='icmp', from_port=-1, to_port=-1, src_group=security_group)
      security_group.authorize(ip_protocol='tcp', from_port=0, to_port=65535, src_group=security_group)
      security_group.authorize(ip_protocol='udp', from_port=0, to_port=65535, src_group=security_group)
    security_group.authorize('tcp', 22, 22, '0.0.0.0/0')

  instance_d = {}
  for (hostname, services) in config.nodes().items():

    if 'worker' in services:
      instance_type = config.get('ec2', 'worker_instance_type')
      num_ephemeral = config.worker_num_ephemeral()
    else:
      instance_type = config.get('ec2', 'default_instance_type')
      num_ephemeral = config.default_num_ephemeral()

    host_ami = config.get_image_id(instance_type)
    if not host_ami:
      exit('ERROR - Image not found for instance type: '+instance_type)

    bdm = BlockDeviceMapping()
    bdm['/dev/sda1'] = BlockDeviceType(delete_on_termination=True)

    for i in range(0, num_ephemeral):
      bdt = BlockDeviceType()
      bdt.ephemeral_name=config.ephemeral_root + str(i)
      bdm[config.device_root + chr(ord('b') + i)] = bdt

    resv = conn.run_instances(key_name=key_name,
                              image_id=host_ami,
                              security_group_ids=[security_group.id],
                              instance_type=instance_type,
                              subnet_id=subnet_id,
                              min_count=1,
                              max_count=1,
                              block_device_map=bdm)
  
    if len(resv.instances) != 1:
      exit('ERROR - Failed to start {0} node'.format(hostname))

    instance = resv.instances[0]

    instance_d[hostname] = instance.id
    print 'Launching {0} node'.format(hostname)

  while True:
    time.sleep(5)

    nodes = get_cluster(conn, config, ['running'])
    num_actual = len(nodes)
    num_expected = len(config.nodes())

    if num_actual == num_expected:
      # Tag instances and create hosts file
      with open(config.hosts_path, 'w') as hosts_file:
        for (hostname, services) in config.nodes().items():
          instance = get_instance(nodes, instance_d[hostname])

          instance.add_tag(key='Name', value='{cn}-{id}'.format(cn=config.cluster_name, id=hostname))
          for tkey, tval in config.instance_tags().iteritems():
            instance.add_tag(key=tkey, value=tval)
          public_ip = ''
          if instance.ip_address:
            public_ip = instance.ip_address
          private_ip = instance.private_ip_address
          print >>hosts_file, hostname, private_ip, public_ip
      print "All {0} nodes have started.  Created hosts file at {1}".format(num_actual, config.hosts_path)
      break
    else:
      print "{0} of {1} nodes have started.  Waiting another 5 sec..".format(num_actual, num_expected)

def get_cluster(conn, config, states):
  reservations = conn.get_all_reservations()
  nodes = []
  for res in reservations:
    active = [i for i in res.instances if i.state in states]
    for inst in active:
      group_names = [g.name for g in inst.groups]
      if (config.cluster_name + "-group") in group_names:
        nodes.append(inst)
  return nodes

def get_active_cluster(conn, config):
  return get_cluster(conn, config, ['pending', 'running', 'stopping', 'stopped'])

def check_code(retcode, command):
  if retcode != 0:
    exit("ERROR - Command failed with return code of {0}: {1}".format(retcode, command))

def exec_on_proxy(config, command, opts=''):
  ssh_command = "ssh -A -o 'StrictHostKeyChecking no' {opts} {usr}@{ldr} '{cmd}'".format(usr=config.get('general', 'cluster_user'),
    ldr=config.proxy_public_ip(), cmd=command, opts=opts)
  return (subprocess.call(ssh_command, shell=True), ssh_command)

def exec_on_proxy_verified(config, command, opts=''):
  (retcode, ssh_command) = exec_on_proxy(config, command, opts)
  check_code(retcode, ssh_command)

def wait_until_proxy_ready(config):
  while True:
    (retcode, ssh_command) = exec_on_proxy(config, 'pwd > /dev/null')
    if retcode == 0:
      print "Proxy is ready!"
      time.sleep(1)
      break;
    print "Proxy is not ready yet.  Will retry in 5 sec..."
    time.sleep(5)  

def execute_playbook(config, playbook):
  print "Executing '{0}' playbook".format(playbook)
  basedir = config.get('general', 'cluster_basedir')
  exec_on_proxy_verified(config, "time -p ansible-playbook {base}/ansible/{playbook}".format(base=basedir, playbook=playbook), opts='-t')

def send_to_proxy(config, path, target, skipIfExists=True): 
  print "Copying to proxy: ",path
  cmd = "scp -o 'StrictHostKeyChecking no'"
  if skipIfExists:
    cmd = "rsync --ignore-existing --progress -e \"ssh -o 'StrictHostKeyChecking no'\""
  subprocess.call("{cmd} {src} {usr}@{ldr}:{tdir}".format(cmd=cmd, src=path, 
          usr=config.get('general', 'cluster_user'), ldr=config.proxy_public_ip(), tdir=target), shell=True)

def get_ec2_conn(config):
  access_key = config.get('ec2', 'aws_access_key')
  secret_key = config.get('ec2', 'aws_secret_key')
  if access_key == 'access_key' or secret_key == 'secret_key':
    exit('ERROR - You must set AWS access & secret keys in fluo-deploy.props')
  region = config.get('ec2', 'region')
  conn = ec2.connect_to_region(region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
  if not conn:
    exit('ERROR - Failed to connect to region ' + region)
  return conn

def sync_cluster(config):
  print 'Syncing ansible directory on {0} cluster proxy node'.format(config.cluster_name)

  vars_d = {}
  for section in ("general", config.get('performance', 'profile')):
    for (name, value) in config.items(section):
      if name not in ('proxy_hostname', 'proxy_socks_port'):
        vars_d[name] = value
  cloud_provider = vars_d.get('cloud_provider', 'ec2')
  if cloud_provider  == 'ec2':
    vars_d["node_type_map"] = str(config.node_type_map())
    vars_d["mount_root"] = config.mount_root
    vars_d["metrics_drive_ids"] = str(config.metrics_drive_ids())
  if cloud_provider == 'baremetal':
    for (name, value) in config.items('baremetal'):
       vars_d[name] = value
    node_type_map = {}
    mounts = vars_d['mounts'].split(",")
    devices = vars_d['devices'].split(",")
    for node_type in 'default', 'worker':
        node_type_map[node_type] = {'mounts': mounts, 'devices': devices }
    vars_d["node_type_map"] = str(node_type_map)
    vars_d["metrics_drive_ids"] = str(vars_d["metrics_drive_ids"].split(","))

  ansible_conf = join(config.deploy_path, "ansible/conf")
  with open(join(ansible_conf, "hosts"), 'w') as hosts_file:
    print >>hosts_file, "[proxy]\n{0}".format(config.get('general', 'proxy_hostname'))
    print >>hosts_file, "\n[accumulomaster]\n{0}".format(config.get_service_hostnames("accumulomaster")[0])
    print >>hosts_file, "\n[namenode]\n{0}".format(config.get_service_hostnames("namenode")[0])
    print >>hosts_file, "\n[resourcemanager]\n{0}".format(config.get_service_hostnames("resourcemanager")[0])

    if config.has_service("metrics"):
      print >>hosts_file, "\n[metrics]\n{0}".format(config.get_service_hostnames("metrics")[0])

    print >>hosts_file, "\n[zookeepers]"
    for (index, zk_host) in enumerate(config.get_service_hostnames("zookeeper"), start=1):
      print >>hosts_file, "{0} id={1}".format(zk_host, index)

    if config.has_service('fluo'):
      print >>hosts_file, "\n[fluo]"
      for host in config.get_service_hostnames("fluo"):
        print >>hosts_file, host

    print >>hosts_file, "\n[workers]"
    for worker_host in config.get_service_hostnames("worker"):
      print >>hosts_file, worker_host

    print >>hosts_file, "\n[accumulo:children]\naccumulomaster\nworkers"
    print >>hosts_file, "\n[hadoop:children]\nnamenode\nresourcemanager\nworkers"

    print >>hosts_file, "\n[nodes]"
    for (private_ip, hostname) in config.get_private_ip_hostnames():
      print >>hosts_file, "{0} ansible_ssh_host={1} node_type={2}".format(hostname, private_ip, config.node_type(hostname))

    print >>hosts_file, "\n[all:vars]"
    for (name, value) in sorted(vars_d.items()):
      print >>hosts_file, "{0} = {1}".format(name, value)

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
        usr=config.get('general', 'cluster_user'), ldr=config.proxy_public_ip(), tdir=basedir), shell=True)

  exec_on_proxy_verified(config, "{0}/ansible/scripts/install_ansible.sh".format(basedir), opts='-t')

def setup_cluster(config):
  print 'Setting up {0} cluster'.format(config.cluster_name)

  sync_cluster(config)

  conf_upload = join(config.deploy_path, "conf/upload")
  accumulo_tarball =  join(conf_upload, "accumulo-{0}-bin.tar.gz".format(config.version("accumulo")))
  fluo_tarball = join(conf_upload, "fluo-{0}-bin.tar.gz".format(config.version("fluo")))
  basedir = config.get('general', 'cluster_basedir')
  cluster_tarballs = "{0}/tarballs".format(basedir)
  exec_on_proxy_verified(config, "mkdir -p {0}".format(cluster_tarballs))
  if isfile(accumulo_tarball):
    send_to_proxy(config, accumulo_tarball, cluster_tarballs)
  if isfile(fluo_tarball) and config.has_service('fluo'):
    send_to_proxy(config, fluo_tarball, cluster_tarballs)

  execute_playbook(config, "site.yml")
      
def main():

  deploy_path = os.environ.get('FLUO_DEPLOY')
  if not deploy_path:
    exit('ERROR - The FLUO_DEPLOY env variable must be set!')
  if not os.path.isdir(deploy_path):
    exit('ERROR - Directory set by FLUO_DEPLOY does not exist: '+deploy_path)

  config_path = join(deploy_path, "conf/fluo-deploy.props")
  if not isfile(config_path):
    exit('ERROR - A config file does not exist at '+config_path)  

  hosts_dir = join(deploy_path, "conf/hosts/")

  # parse command line args
  retval = parse_args(hosts_dir)
  if not retval:
    print "Invalid command line arguments. For help, use 'fluo-deploy -h'"
    sys.exit(1)
  (opts, action, args) = retval

  hosts_path = join(hosts_dir, opts.cluster)

  config = DeployConfig(deploy_path, config_path, hosts_path, opts.cluster)
  config.verify_config(action)

  if action == 'launch':
    conn = get_ec2_conn(config)
    launch_cluster(conn, config)
  elif action == 'status':
    conn = get_ec2_conn(config)
    nodes = get_cluster(conn, config, ['running'])
    print "Found {0} nodes in {1} cluster".format(len(nodes), config.cluster_name)
    for node in nodes:
      print "  ", node.tags.get('Name', 'UNKNOWN_NAME'), node.id, node.private_ip_address, node.ip_address
  elif action == 'sync':
    sync_cluster(config)
  elif action == 'setup':
    setup_cluster(config)
  elif action == 'config':
    if opts.property == 'all':
      config.print_all()
    else:
      config.print_property(opts.property)
  elif action == 'ssh':
    print "Connecting to proxy: {0} {1}".format(config.get('general', 'proxy_hostname'), config.proxy_public_ip())
    wait_until_proxy_ready(config)
    fwd = ''
    if config.has_option('general', 'proxy_socks_port'):
      fwd = "-D "+config.get('general', 'proxy_socks_port')
    ssh_command = "ssh -C -A -o 'StrictHostKeyChecking no' {fwd} {usr}@{ldr}".format(usr=config.get('general', 'cluster_user'),
      ldr=config.proxy_public_ip(), fwd=fwd)
    retcode = subprocess.call(ssh_command, shell=True)
    check_code(retcode, ssh_command)
  elif action == 'wipe':
    if not isfile(hosts_path):
      exit("Hosts file does not exist for cluster: "+hosts_path)
    print "Killing all processes and wiping data from {0} cluster".format(config.cluster_name)
    execute_playbook(config, "wipe.yml")
  elif action == 'run':
    app = opts.application
    repo = config.get('apps', app + '_repo')
    branch = config.get('apps', app + '_branch')
    command = config.get('apps', app + '_command')

    run_args = "{0} {1} {2} {3}".format(app, repo, branch, command)
    if opts.app_args:
      run_args = "{0} {1}".format(run_args, opts.app_args)
  
    basedir = config.get('general', 'cluster_basedir')
    exec_on_proxy_verified(config, "{0}/apps/run.sh {1}".format(basedir, run_args), opts='-t')
  elif action == 'terminate':
    conn = get_ec2_conn(config)
    nodes = get_active_cluster(conn, config)

    if len(nodes) == 0:
      exit("No nodes running in {0} cluster to terminate".format(config.cluster_name))

    print "The following {0} nodes in {1} cluster will be terminated:".format(len(nodes), config.cluster_name)
    for node in nodes:
      print "  ", node.tags.get('Name', 'UNKNOWN_NAME'), node.id, node.private_ip_address, node.ip_address

    response = raw_input("Do you want to continue? (y/n) ")
    if response == "y":
      for node in nodes:
        node.terminate()
      print "Terminated instances"

      if isfile(hosts_path):
        os.remove(hosts_path)
        print "Removed hosts file at ",hosts_path
    else:
      print "Aborted termination"
  else:
    print 'ERROR - Unknown action:', action

main()
