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

from ConfigParser import ConfigParser
from util import get_num_ephemeral, exit
import os
from os.path import join

SERVICES = ['zookeeper', 'namenode', 'resourcemanager', 'accumulomaster', 'worker', 'fluo', 'graphite', 'dev']

class DeployConfig(ConfigParser):

  def __init__(self, deploy_path, config_path, hosts_path, cluster_name):
    ConfigParser.__init__(self)
    self.deploy_path = deploy_path
    self.read(config_path)
    self.hosts_path = hosts_path
    self.cluster_name = cluster_name
    self.node_d = None
    self.hosts = None
    self.init_nodes()

  def verify_config(self, action):
    proxy = self.proxy_hostname()
    if not proxy:
      exit("ERROR - proxy.hostname must be set in fluo-deploy.props")

    if proxy not in self.node_d:
      exit("ERROR - The proxy (set by property proxy.hostname={0}) cannot be found in 'nodes' section of fluo-deploy.props".format(proxy))

    if action != 'launch':
      self.proxy_public_ip()

    if action in ['launch', 'setup']:
      for service in SERVICES:
        if service not in ['fluo', 'graphite', 'dev']:
          if not self.has_service(service):
            exit("ERROR - Missing '{0}' service from [nodes] section of fluo-deploy.props".format(service))

  def init_nodes(self):
    self.node_d = {}
    for (hostname, value) in self.items('nodes'):
      if hostname in self.node_d:
        exit('Hostname {0} already exists twice in nodes'.format(hostname))
      service_list = []
      for service in value.split(','):
        if service in SERVICES:
          service_list.append(service)
        else:
          exit('Unknown service "%s" declared for node %s' % (service, hostname))
      self.node_d[hostname] = service_list

  def cluster_username(self):
    return self.get('general', 'cluster.username')

  def cluster_base_dir(self):
    return self.get('general', 'cluster.base.dir')

  def accumulo_instance(self):
    return self.get('general', 'accumulo.instance')

  def accumulo_password(self):
    return self.get('general', 'accumulo.password')

  def proxy_hostname(self):
    return self.get('general', 'proxy.hostname')

  def proxy_socks_port(self):
    if self.has_option('general', 'proxy.socks.port'):
      return self.get('general', 'proxy.socks.port')

  def configure_cluster(self):
    if self.has_option('general', 'configure.cluster'):
      return self.get('general', 'configure.cluster')

  def cluster_install_dir(self):
    return join(self.cluster_base_dir(), "install")

  def local_install_dir(self):
    return join(self.deploy_path, "cluster/install")

  def default_num_ephemeral(self):
    return get_num_ephemeral(self.default_instance_type())

  def worker_num_ephemeral(self):
    return get_num_ephemeral(self.worker_instance_type())

  def num_ephemeral(self, hostname):
    if 'worker' in self.node_d[hostname]:
      return self.worker_num_ephemeral()
    else:
      return self.default_num_ephemeral()

  def data_dir(self):
    return "/media/ephemeral0"

  def ephemeral_dirs(self, suffix, num_ephemeral):
    dirs = ""
    sep = ""
    for i in range(0, num_ephemeral):
      dirs = dirs + sep + "/media/ephemeral"+str(i)+suffix
      sep = ","
    return dirs

  def worker_ephemeral_dirs(self, suffix):
    return self.ephemeral_dirs(suffix, self.worker_num_ephemeral())

  def hadoop_prefix(self):
    return join(self.cluster_install_dir(), "hadoop-"+self.hadoop_version())

  def zookeeper_home(self):
    return join(self.cluster_install_dir(), 'zookeeper-'+self.zookeeper_version())

  def cluster_tarballs_dir(self):
    return join(self.cluster_base_dir(), "tarballs")

  def local_tarballs_dir(self):
    return join(self.deploy_path, "cluster/tarballs")

  def apache_mirror(self):
    return self.get('general', 'apache.mirror')

  def accumulo_version(self):
    return self.get('general', 'accumulo.version')

  def accumulo_md5(self):
    return self.get('general', 'accumulo.md5.hash')

  def fluo_version(self):
    return self.get('general', 'fluo.version')

  def hadoop_version(self):
    return self.get('general', 'hadoop.version')

  def hadoop_md5(self):
    return self.get('general', 'hadoop.md5.hash')

  def zookeeper_version(self):
    return self.get('general', 'zookeeper.version')

  def zookeeper_md5(self):
    return self.get('general', 'zookeeper.md5.hash')

  def spark_version(self):
    return self.get('general', 'spark.version')

  def spark_md5(self):
    return self.get('general', 'spark.md5.hash')

  def accumulo_tarball(self):
    return 'accumulo-%s-bin.tar.gz' % self.accumulo_version()

  def hadoop_tarball(self):
    return 'hadoop-%s.tar.gz' % self.hadoop_version()

  def zookeeper_tarball(self): 
    return 'zookeeper-%s.tar.gz' % self.zookeeper_version()
 
  def accumulo_url(self):
    return '%s/accumulo/%s/%s' % (self.apache_mirror(), self.accumulo_version(), self.accumulo_tarball())

  def hadoop_url(self):
    return '%s/hadoop/common/hadoop-%s/%s' % (self.apache_mirror(), self.hadoop_version(), self.hadoop_tarball())

  def zookeeper_url(self): 
    return '%s/zookeeper/zookeeper-%s/%s' % (self.apache_mirror(), self.zookeeper_version(), self.zookeeper_tarball())

  def accumulo_path(self): 
    return join(self.deploy_path, "cluster/tarballs/"+self.accumulo_tarball())

  def hadoop_path(self): 
    return join(self.deploy_path, "cluster/tarballs/"+self.hadoop_tarball())

  def zookeeper_path(self): 
    return join(self.deploy_path, "cluster/tarballs/"+self.zookeeper_tarball())

  def zookeeper_connect(self):
    return ",".join(self.get_service_hostnames("zookeeper"))

  def zookeeper_server_config(self):
    return "\n".join(["server.{0}={1}:2888:3888".format(index, server) for (index, server) in enumerate(self.get_service_hostnames("zookeeper"), start=1)])

  def default_instance_type(self):
    return self.get('ec2', 'default.instance.type')

  def worker_instance_type(self):
    return self.get('ec2', 'worker.instance.type')

  def region(self):
    return self.get('ec2', 'region')

  def vpc_id(self):
    if self.has_option('ec2', 'vpc.id'):
      return self.get('ec2', 'vpc.id')

  def subnet_id(self):
    if self.has_option('ec2', 'subnet.id'):
      return self.get('ec2', 'subnet.id')

  def key_name(self):
    if self.has_option('ec2', 'key.name'):
      val = self.get('ec2', 'key.name')
      if val:
        return val

  def instance_tags(self):
    retd = {}
    if self.has_option('ec2', 'instance.tags'):
      value = self.get('ec2', 'instance.tags')
      if value:
        for kv in value.split(','):
          (key, val) = kv.split(':')
          retd[key] = val
    return retd

  def ebs_root_size(self):
    if self.has_option('ec2', 'ebs.root.size'):
      return int(self.get('ec2', 'ebs.root.size'))
    else:
      return 0

  def nodes(self):
    return self.node_d

  def get_node(self, hostname):
    return self.node_d[hostname]

  def has_service(self, service):
    for (hostname, service_list) in self.node_d.items():
      if service in service_list:
        return True
    return False

  def get_host_services(self):
    retval = []
    for (hostname, service_list) in self.node_d.items():
      retval.append((hostname, ' '.join(service_list)))
    retval.sort()
    return retval

  def get_service_private_ips(self, service):
    retval = []
    for (hostname, service_list) in self.node_d.items():
      if service in service_list:
        retval.append(self.get_private_ip(hostname))
    retval.sort()
    return retval

  def get_service_hostnames(self, service):
    retval = []
    for (hostname, service_list) in self.node_d.items():
      if service in service_list:
        retval.append(hostname)
    retval.sort()
    return retval

  def get_non_proxy(self):
    retval = []
    proxy_ip = self.get_private_ip(self.proxy_hostname())
    for (hostname, (private_ip, public_ip)) in self.hosts.items():
      if private_ip != proxy_ip:
        retval.append((private_ip, hostname))
    retval.sort()
    return retval

  def parse_hosts(self):
    if not os.path.isfile(self.hosts_path):
      exit('ERROR - A hosts file does not exist at %s' % self.hosts_path)  

    self.hosts = {} 
    with open(self.hosts_path) as f:
      for line in f:
        line = line.strip()
        if line.startswith("#") or not line:
          continue
        args = line.split(' ')
        if len(args) == 2:
          self.hosts[args[0]] = (args[1], None)
        elif len(args) == 3:
          self.hosts[args[0]] = (args[1], args[2])
        else:
          exit('ERROR - Bad line %s in hosts %s' % (line, self.hosts_path))
        
  def get_hosts(self):
    if self.hosts is None:
      self.parse_hosts()
    return self.hosts

  def get_private_ip(self, hostname):
    return self.get_hosts()[hostname][0]

  def get_public_ip(self, hostname):
    return self.get_hosts()[hostname][1]

  def proxy_public_ip(self):
    retval = self.get_public_ip(self.proxy_hostname())
    if not retval:
      exit("ERROR - Leader {0} does not have a public IP".format(self.proxy_hostname()))
    return retval

  def proxy_private_ip(self):
    return self.get_private_ip(self.proxy_hostname())

  def print_all(self):
    print 'proxy.public.ip = ', self.proxy_public_ip()
    for (name, val) in self.items('general'):
      print name, '=', val

    for (name, val) in self.items('ec2'):
      print name, '=', val

  def print_property(self, key):

    if key == 'proxy.public.ip':
      print self.proxy_public_ip()
      return
    else:
      for section in self.sections():
        if self.has_option(section, key):
          print self.get(section, key)
          return

    exit("Property '{0}' was not found".format(key))
