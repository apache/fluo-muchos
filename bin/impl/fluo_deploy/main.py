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
from util import get_image_id, setup_boto, parse_args, exit
from os.path import isfile, join
from string import Template
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
  if not config.key_name():
    exit('ERROR - key.name is not set fluo-deploy.props')

  cur_nodes = get_active_cluster(conn, config)
  if cur_nodes:
    exit('ERROR - There are already instances running for {0} cluster'.format(config.cluster_name))

  if isfile(config.hosts_path):
    exit("ERROR - A hosts file already exists at {0}.  Please delete before running launch again".format(config.hosts_path))

  if not config.proxy_hostname():
    exit("ERROR - proxy.hostname must specified in fluo-deploy.props file")

  print "Launching {0} cluster".format(config.cluster_name)

  security_group = get_or_make_group(conn, config.cluster_name + "-group", config.vpc_id())
  if security_group.rules == []: # Group was just now created
    if config.vpc_id() is None:
      security_group.authorize(src_group=security_group)
    else:
      security_group.authorize(ip_protocol='icmp', from_port=-1, to_port=-1, src_group=security_group)
      security_group.authorize(ip_protocol='tcp', from_port=0, to_port=65535, src_group=security_group)
      security_group.authorize(ip_protocol='udp', from_port=0, to_port=65535, src_group=security_group)
    security_group.authorize('tcp', 22, 22, '0.0.0.0/0')

  instance_d = {}
  for (hostname, services) in config.nodes().items():

    if 'worker' in services:
      instance_type = config.worker_instance_type()
      num_ephemeral = config.worker_num_ephemeral()
    else:
      instance_type = config.default_instance_type()
      num_ephemeral = config.default_num_ephemeral()

    host_ami = get_image_id(instance_type)
    if not host_ami:
      exit('ERROR - Image not found for instance type: '+instance_type)

    bdm = BlockDeviceMapping()
    if config.ebs_root_size() > 0 :
      bdt = BlockDeviceType()
      bdt.size = config.ebs_root_size()
      bdt. delete_on_termination = True
      bdm['/dev/sda1'] = bdt

    for i in range(0, num_ephemeral):
      bdt = BlockDeviceType()
      bdt.ephemeral_name='ephemeral' + str(i)
      bdm['/dev/xvd' + chr(ord('b') + i)] = bdt

    resv = conn.run_instances(key_name=config.key_name(),
                              image_id=host_ami,
                              security_group_ids=[security_group.id],
                              instance_type=instance_type,
                              subnet_id=config.subnet_id(),
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
  ssh_command = "ssh -A -o 'StrictHostKeyChecking no' {opts} {usr}@{ldr} '{cmd}'".format(usr=config.cluster_username(),
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

def wait_until_cluster_ready(config):
  wait_until_proxy_ready(config)
  exec_fluo_cluster_command(config, "ready")
 
def exec_fluo_cluster_command(config, command):
  exec_on_proxy_verified(config, "bash {base}/install/fluo-cluster/bin/fluo-cluster {command}".format(base=config.cluster_base_dir(), command=command))

def send_to_proxy(config, path, target, skipIfExists=True): 
  print "Copying to proxy: ",path
  cmd = "scp -o 'StrictHostKeyChecking no'"
  if skipIfExists:
    cmd = "rsync --ignore-existing --progress -e \"ssh -o 'StrictHostKeyChecking no'\""
  subprocess.call("{cmd} {src} {usr}@{ldr}:{tdir}".format(cmd=cmd, src=path, 
          usr=config.cluster_username(), ldr=config.proxy_public_ip(), tdir=target), shell=True)

def get_ec2_conn(config):
  conn = ec2.connect_to_region(config.region())
  if not conn:
    exit('ERROR - Failed to connect to region ' + config.region())
  return conn

def write_test_props(config):
  conf_install = join(config.deploy_path, "cluster/install/fluo-cluster/conf")

  test_props_path = join(conf_install, "test.properties")
  with open(test_props_path, 'w') as test_props_file:
    for (name, value) in config.items("test"):
      print >>test_props_file, "{0}={1}".format(name, value)

def setup_cluster(config):

  accumulo_tarball =  join(config.local_tarballs_dir(), "accumulo-{0}-bin.tar.gz".format(config.accumulo_version()))

  if config.has_service('fluo'): 
    fluo_tarball = join(config.local_tarballs_dir(), "fluo-{0}-bin.tar.gz".format(config.fluo_version()))
    if not isfile(fluo_tarball):
      exit("Please create a Fluo tarball and copy it to "+fluo_tarball)

  print 'Setting up {0} cluster'.format(config.cluster_name)
  conf_templates = join(config.deploy_path, "cluster/templates/fluo-cluster/conf")
  conf_install = join(config.deploy_path, "cluster/install/fluo-cluster/conf")

  # copy keys file to conf (if it exists)
  conf_keys = join(config.deploy_path, "conf/keys")
  install_keys = join(config.deploy_path, "cluster/install/fluo-cluster/conf/keys")
  if isfile(conf_keys):
    shutil.copyfile(conf_keys, install_keys)

  sub_d = {}
  sub_d["BASE_DIR"] = config.cluster_base_dir()
  sub_d["CLUSTER_USERNAME"] = config.cluster_username()
  sub_d["CONFIGURE_CLUSTER"] = config.configure_cluster()
  sub_d["APACHE_MIRROR"] = config.apache_mirror()
  sub_d["ACCUMULO_VERSION"] = config.accumulo_version()
  sub_d["ACCUMULO_MD5"] = config.accumulo_md5()
  sub_d["FLUO_VERSION"] = config.fluo_version()
  sub_d["HADOOP_VERSION"] = config.hadoop_version()
  sub_d["HADOOP_MD5"] = config.hadoop_md5()
  sub_d["ZOOKEEPER_VERSION"] = config.zookeeper_version()
  sub_d["ZOOKEEPER_MD5"] = config.zookeeper_md5()
  sub_d["DATA_DIR"] = config.data_dir()
  sub_d["HADOOP_PREFIX"] = config.hadoop_prefix()
  sub_d["ZOOKEEPER_HOME"] = config.zookeeper_home()
  sub_d["ZOOKEEPERS"] = config.zookeeper_connect()
  sub_d["ZOOKEEPER_SERVER_CONFIG"] = config.zookeeper_server_config()
  sub_d["NAMENODE_HOST"] = config.get_service_private_ips("namenode")[0]
  sub_d["RESOURCEMANAGER_HOST"] = config.get_service_private_ips("resourcemanager")[0]
  sub_d["ACCUMULOMASTER_HOST"] = config.get_service_hostnames("accumulomaster")[0]
  sub_d["NUM_WORKERS"] = len(config.get_service_hostnames("worker"))
  sub_d["PROXY_HOST"] = config.proxy_hostname()
  sub_d["ACCUMULO_INSTANCE"] = config.accumulo_instance()
  sub_d["ACCUMULO_PASSWORD"] = config.accumulo_password()
  sub_d["DATANODE_DIRS"] = config.worker_ephemeral_dirs("/hadoop/data")
  sub_d["MAPRED_TEMP_DIRS"] = config.worker_ephemeral_dirs("/hadoop/mapred/temp")
  sub_d["MAPRED_LOCAL_DIRS"] = config.worker_ephemeral_dirs("/hadoop/mapred/local")
  sub_d["YARN_LOCAL_DIRS"] = config.worker_ephemeral_dirs("/hadoop/yarn/local")

  if config.has_service("graphite"):
    sub_d["GRAPHITE_SERVER"] = config.get_service_private_ips("graphite")[0]
  
  for fn in os.listdir(conf_templates):
    if not config.has_service("graphite") and fn == "metrics.yaml":
      continue
    template_path = join(conf_templates, fn)
    install_path = join(conf_install, fn)
    if isfile(install_path):
      os.remove(install_path)
    if isfile(template_path) and not template_path.startswith('.'):
      with open(template_path, "r") as template_file:
        template_data = template_file.read()
        template = Template(template_data)
        sub_data = template.substitute(sub_d)
        with open(install_path, "w") as install_file:
          install_file.write(sub_data)

  write_test_props(config)

  ael_path = join(conf_install, "hosts/all_except_proxy")
  with open(ael_path, 'w') as ael_file:
    for (private_ip, hostname) in config.get_non_proxy():
      print >>ael_file, private_ip

  llast_path = join(conf_install, "hosts/all_for_configure")
  with open(llast_path, 'w') as llast_file:
    for (private_ip, hostname) in config.get_non_proxy():
      print >>llast_file, private_ip, hostname, config.num_ephemeral(hostname)
    proxy_host = config.proxy_hostname()
    print >>llast_file, config.get_private_ip(proxy_host), proxy_host, config.num_ephemeral(proxy_host)

  services_path = join(conf_install, "hosts/hosts_with_services")
  with open(services_path, 'w') as services_file:
    for (host, services) in config.get_host_services():
      print >>services_file, host, services

  aht_path = join(conf_install, "hosts/all_hosts")
  with open(aht_path, 'w') as aht_file:
    for (host, services) in config.get_host_services():
      print >>aht_file, host

  aip_path = join(conf_install, "hosts/all_ips")
  with open(aip_path, 'w') as aip_file:
    for (host, services) in config.get_host_services():
      print >>aip_file, config.get_private_ip(host)

  workers_path = join(conf_install, "hosts/workers")
  with open(workers_path, 'w') as workers_file:
    for worker_host in config.get_service_hostnames("worker"):
      print >>workers_file, worker_host

  zk_path = join(conf_install, "hosts/zookeepers")
  with open(zk_path, 'w') as zk_file:
    for zk_host in config.get_service_hostnames("zookeeper"):
      print >>zk_file, zk_host

  zkid_path = join(conf_install, "hosts/zookeeper_ids")
  with open(zkid_path, 'w') as zkid_file:
    for (index, zk_host) in enumerate(config.get_service_hostnames("zookeeper"), start=1):
      print >>zkid_file, zk_host, index

  with open(join(conf_install, "hosts/accumulomaster"), 'w') as am_file:
    print >>am_file, config.get_service_hostnames("accumulomaster")[0]

  with open(join(conf_install, "hosts/append_to_hosts"), 'w') as ath_file:
    for (hostname, (private_ip, public_ip)) in config.get_hosts().items():
      print >>ath_file, private_ip, hostname

  install_tarball = join(config.local_tarballs_dir(), "install.tar.gz")
  if isfile(install_tarball):
    os.remove(install_tarball)

  retcode = subprocess.call("cd {0}; tar czf tarballs/install.tar.gz install".format(join(config.deploy_path, "cluster")), shell=True)
  if retcode != 0:
    error("Failed to create install tarball")

  wait_until_proxy_ready(config)

  exec_on_proxy_verified(config, "mkdir -p {0}".format(config.cluster_tarballs_dir()))
  send_to_proxy(config, install_tarball, config.cluster_tarballs_dir(), skipIfExists=False)

  if isfile(accumulo_tarball):
    send_to_proxy(config, accumulo_tarball, config.cluster_tarballs_dir())

  if config.has_service('fluo'):
    send_to_proxy(config, fluo_tarball, config.cluster_tarballs_dir())

  exec_on_proxy_verified(config, "rm -rf {base}/install; tar -C {base} -xzf {base}/tarballs/install.tar.gz".format(base=config.cluster_base_dir()))

  exec_fluo_cluster_command(config, "setup")

  wait_until_cluster_ready(config)
 
  exec_fluo_cluster_command(config, "init")
      
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
  (opts, action) = retval

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
  elif action == 'setup':
    setup_cluster(config)
  elif action == 'config':
    if opts.property == 'all':
      config.print_all()
    else:
      config.print_property(opts.property)
  elif action == 'ssh':
    print "Connecting to proxy: {0} {1}".format(config.proxy_hostname(), config.proxy_public_ip())
    wait_until_proxy_ready(config)
    fwd = ''
    if config.proxy_socks_port():
      fwd = "-D "+config.proxy_socks_port()
    ssh_command = "ssh -A -o 'StrictHostKeyChecking no' {fwd} {usr}@{ldr}".format(usr=config.cluster_username(),
      ldr=config.proxy_public_ip(), fwd=fwd)
    retcode = subprocess.call(ssh_command, shell=True)
    check_code(retcode, ssh_command)
  elif action == 'kill':
    if not isfile(hosts_path):
      exit("Hosts file does not exist for cluster: "+hosts_path)
    print "Killing {0} cluster".format(config.cluster_name)
    exec_fluo_cluster_command(config, "kill")
  elif action == 'test':
    write_test_props(config)
    send_to_proxy(config, join(config.deploy_path, "cluster/install/fluo-cluster/conf/test.properties"), join(config.cluster_install_dir(), "fluo-cluster/conf"), skipIfExists=False)
    exec_fluo_cluster_command(config, "test {0}".format(opts.application))
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
