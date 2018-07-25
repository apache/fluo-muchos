# Copyright 2014 Muchos authors (see AUTHORS)
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
from sys import exit
from util import get_ephemeral_devices, get_arch
import os

SERVICES = ['zookeeper', 'namenode', 'resourcemanager', 'accumulomaster', 'mesosmaster', 'worker', 'fluo', 'fluo_yarn', 'metrics', 'spark']


class DeployConfig(ConfigParser):

    def __init__(self, deploy_path, config_path, hosts_path, cluster_name):
        ConfigParser.__init__(self)
        self.optionxform = str
        self.deploy_path = deploy_path
        self.read(config_path)
        self.hosts_path = hosts_path
        self.cluster_name = cluster_name
        self.sg_name = cluster_name + '-group'
        self.ephemeral_root = 'ephemeral'
        self.mount_root = '/media/' + self.ephemeral_root
        self.metrics_drive_root = 'media-' + self.ephemeral_root
        self.node_d = None
        self.hosts = None
        self.init_nodes()

    def verify_config(self, action):
        proxy = self.get('general', 'proxy_hostname')
        if not proxy:
            exit("ERROR - proxy.hostname must be set in muchos.props")

        if proxy not in self.node_d:
            exit("ERROR - The proxy (set by property proxy_hostname={0}) cannot be found in 'nodes' section of "
                 "muchos.props".format(proxy))

        if action in ['launch', 'setup']:
            for service in SERVICES:
                if service not in ['fluo', 'fluo_yarn', 'metrics', 'mesosmaster', 'spark']:
                    if not self.has_service(service):
                        exit("ERROR - Missing '{0}' service from [nodes] section of muchos.props".format(service))

    def verify_launch(self):
        self.verify_instance_type(self.get('ec2', 'default_instance_type'))
        self.verify_instance_type(self.get('ec2', 'worker_instance_type'))

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

    def default_ephemeral_devices(self):
        return get_ephemeral_devices(self.get('ec2', 'default_instance_type'))

    def worker_ephemeral_devices(self):
        return get_ephemeral_devices(self.get('ec2', 'worker_instance_type'))

    def max_ephemeral(self):
        return max((len(self.default_ephemeral_devices()), len(self.worker_ephemeral_devices())))

    def node_type_map(self):
        node_types = {}
        node_list = [('default', self.default_ephemeral_devices()), ('worker', self.worker_ephemeral_devices())]

        for (ntype, devices) in node_list:
            node_types[ntype] = {'mounts': self.mounts(len(devices)), 'devices': devices}
        return node_types

    def node_type(self, hostname):
        if 'worker' in self.node_d[hostname]:
            return 'worker'
        return 'default'

    def mounts(self, num_ephemeral):
        mounts = []
        for i in range(0, num_ephemeral):
            mounts.append(self.mount_root + str(i))
        return mounts

    def fstype(self):
        retval = self.get('ec2', 'fstype')
        if not retval:
            return 'ext3'
        return retval

    def force_format(self):
        retval = self.get('ec2', 'force_format')
        if not retval:
            return 'no'
        return retval

    def metrics_drive_ids(self):
        drive_ids = []
        for i in range(0, self.max_ephemeral()):
            drive_ids.append(self.metrics_drive_root + str(i))
        return drive_ids

    def version(self, software_id):
        return self.get('general', software_id + '_version')

    def sha256(self, software_id):
        return self.get('general', software_id + '_sha256')

    def verify_instance_type(self, instance_type):
        if get_arch(instance_type) == 'pvm':
            exit("ERROR - Configuration contains instance type '{0}' that uses pvm architecture."
                 "Only hvm architecture is supported!".format(instance_type))

    def instance_tags(self):
        retd = {}
        if self.has_option('ec2', 'instance_tags'):
            value = self.get('ec2', 'instance_tags')
            if value:
                for kv in value.split(','):
                    (key, val) = kv.split(':')
                    retd[key] = val
        return retd

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
        proxy_ip = self.get_private_ip(self.get('general', 'proxy_hostname'))
        for (hostname, (private_ip, public_ip)) in self.get_hosts().items():
            if private_ip != proxy_ip:
                retval.append((private_ip, hostname))
        retval.sort()
        return retval

    def get_private_ip_hostnames(self):
        retval = []
        for (hostname, (private_ip, public_ip)) in self.get_hosts().items():
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

    def proxy_hostname(self):
        return self.get('general', 'proxy_hostname')

    def proxy_public_ip(self):
        retval = self.get_public_ip(self.proxy_hostname())
        if not retval:
            exit("ERROR - Proxy '{0}' does not have a public IP".format(self.proxy_hostname()))
        return retval

    def get_proxy_ip(self):
        proxy_host = self.proxy_hostname()
        ip = self.get_public_ip(proxy_host)
        if not ip:
            ip = self.get_private_ip(proxy_host)
        return ip

    def proxy_private_ip(self):
        return self.get_private_ip(self.proxy_hostname())

    def get_performance_prop(self, prop):
        profile = self.get('performance', 'profile')
        return self.get(profile, prop)

    def print_all(self):
        print 'proxy_public_ip = ', self.proxy_public_ip()
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


HOST_VAR_DEFAULTS = {
  'accumulo_home': '"{{ install_dir }}/accumulo-{{ accumulo_version }}"',
  'accumulo_instance': None,
  'accumulo_major_version': '"{{ accumulo_version.split(\'.\')[0] }}"',
  'accumulo_password': None,
  'accumulo_tarball': 'accumulo-{{ accumulo_version }}-bin.tar.gz',
  'accumulo_version': None,
  'cloud_provider': None,
  'cluster_basedir': None,
  'cluster_user': None,
  'default_data_dirs': None,
  'fluo_home': '"{{ install_dir }}/fluo-{{ fluo_version }}"',
  'fluo_tarball': 'fluo-{{ fluo_version }}-bin.tar.gz',
  'fluo_version': None,
  'fluo_yarn_home': '"{{ install_dir }}/fluo-yarn-{{ fluo_yarn_version }}"',
  'fluo_yarn_tarball': 'fluo-yarn-{{ fluo_yarn_version }}-bin.tar.gz',
  'fluo_yarn_version': None,
  'hadoop_prefix': '"{{ install_dir }}/hadoop-{{ hadoop_version }}"',
  'hadoop_tarball': 'hadoop-{{ hadoop_version }}.tar.gz',
  'hadoop_version': None,
  'hdfs_root': 'hdfs://{{ groups[\'namenode\'][0] }}:8020',
  'install_dir': '"{{ cluster_basedir }}/install"',
  'java_home': '"/usr/lib/jvm/java-1.8.0-openjdk"',
  'maven_home': '"{{ install_dir }}/apache-maven-{{ maven_version }}"',
  'maven_tarball': 'apache-maven-{{ maven_version }}-bin.tar.gz',
  'maven_version': '3.2.5',
  'spark_home': '"{{ install_dir }}/spark-{{ spark_version }}-bin-without-hadoop"',
  'spark_tarball': 'spark-{{ spark_version }}-bin-without-hadoop.tgz',
  'spark_version': None,
  'tarballs_dir': '"{{ cluster_basedir }}/tarballs"',
  'worker_data_dirs': None,
  'zookeeper_connect': '"{{ groups[\'zookeepers\']|join(\',\') }}"',
  'zookeeper_client_port': '"2181"',
  'zookeeper_home': '"{{ install_dir }}/zookeeper-{{ zookeeper_version }}"',
  'zookeeper_tarball': 'zookeeper-{{ zookeeper_version }}.tar.gz',
  'zookeeper_version': None
}

PLAY_VAR_DEFAULTS = {
  'accumulo_dcache_size': None,
  'accumulo_icache_size': None,
  'accumulo_imap_size': None,
  'accumulo_sha256': None,
  'accumulo_tserv_mem': None,
  'fluo_worker_instances_multiplier': None,
  'fluo_worker_mem_mb': None,
  'fluo_worker_threads': None,
  'force_format': None,
  'fstype': None,
  'fluo_sha256': None,
  'fluo_yarn_sha256': None,
  'hadoop_sha256': None,
  'hub_version': '2.2.3',
  'hub_home': '"{{ install_dir }}/hub-linux-amd64-{{ hub_version }}"',
  'hub_tarball': 'hub-linux-amd64-{{ hub_version }}.tgz',
  'hub_sha256': '54c35a459a4241b7ae4c28bcfea0ceef849dd2f8a9dd2b82ba2ba964a743e6bc',
  'maven_sha256': '8c190264bdf591ff9f1268dc0ad940a2726f9e958e367716a09b8aaa7e74a755',
  'metrics_drive_ids': None,
  'mount_root': None,
  'node_type_map': None,
  'network_interface': None,
  'spark_sha256': None,
  'shutdown_delay_minutes': None,
  'twill_reserve_mem_mb': None,
  'yarn_nm_mem_mb': None,
  'zookeeper_sha256': None
}
