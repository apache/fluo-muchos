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

from configparser import ConfigParser
from sys import exit
from .util import get_ephemeral_devices, get_arch
import os
import json
import glob

SERVICES = ['zookeeper', 'namenode', 'resourcemanager', 'accumulomaster', 'mesosmaster', 'worker', 'fluo', 'fluo_yarn', 'metrics', 'spark', 'client', 'swarmmanager', 'journalnode', 'zkfc', 'elkserver']

OPTIONAL_SERVICES = ['fluo', 'fluo_yarn', 'metrics', 'mesosmaster', 'spark', 'client', 'swarmmanager', 'journalnode', 'zkfc']


class DeployConfig(ConfigParser):

    def __init__(self, deploy_path, config_path, hosts_path, checksums_path, templates_path, cluster_name):
        ConfigParser.__init__(self)
        self.optionxform = str
        self.deploy_path = deploy_path
        self.read(config_path)
        self.hosts_path = hosts_path
        self.cluster_name = cluster_name
        self.sg_name = cluster_name + '-group'
        self.ephemeral_root = 'ephemeral'
        self.cluster_type = self.get('general', 'cluster_type')
        self.metrics_drive_root = 'media-' + self.ephemeral_root
        self.node_d = None
        self.hosts = None
        self.checksums_path = checksums_path
        self.checksums_d = None
        self.init_nodes()
        self.cluster_template_d = None
        self.init_template(templates_path)

    def verify_config(self, action):
        proxy = self.get('general', 'proxy_hostname')
        cluster_type = self.get('general', 'cluster_type')
        if cluster_type not in ['azure']:
            if not proxy:
                exit("ERROR - proxy.hostname must be set in muchos.props")

            if proxy not in self.node_d:
                exit("ERROR - The proxy (set by property proxy_hostname={0}) cannot be found in 'nodes' section of "
                     "muchos.props".format(proxy))

        if action in ['launch', 'setup']:
            for service in SERVICES:
                if service not in OPTIONAL_SERVICES:
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
        if self.cluster_template_d:
            return self.cluster_template_d['devices']

        node_types = {}
        if self.get_cluster_type() == 'ec2':
            node_list = [('default', self.default_ephemeral_devices()), ('worker', self.worker_ephemeral_devices())]

            for (ntype, devices) in node_list:
                node_types[ntype] = {'mounts': self.mounts(len(devices)), 'devices': devices}
        return node_types

    def node_type(self, hostname):
        if 'worker' in self.node_d[hostname]:
            return 'worker'
        return 'default'

    def user_home(self):
        return self.get('general', 'user_home')

    def mounts(self, num_ephemeral):
        mounts = []
        for i in range(0, num_ephemeral):
            mounts.append(self.mount_root() + str(i))
        return mounts

    def mount_root(self):
        if self.get_cluster_type() == 'ec2':
            return '/media/' + self.ephemeral_root
        elif self.get_cluster_type() == 'existing':
            return self.get('existing', 'mount_root')
        elif self.get_cluster_type() == 'azure':
            return self.get('azure', 'mount_root')

    def fstype(self):
        retval = None
        if self.get_cluster_type() == 'ec2':
            retval = self.get('ec2', 'fstype')
            if not retval:
                return 'ext3'
        return retval

    def force_format(self):
        retval = 'no'
        if self.get_cluster_type() == 'ec2':
            retval = self.get('ec2', 'force_format')
            if not retval:
                return 'no'
        return retval

    def data_dirs_common(self, nodeType):
        data_dirs = []

        if self.get_cluster_type() == 'ec2':
            data_dirs = self.node_type_map()[nodeType]['mounts']
        elif self.get_cluster_type() == 'existing':
            data_dirs = self.get('existing', 'data_dirs').split(",")
        elif self.get_cluster_type() == 'azure':
            num_disks = int(self.get("azure", "numdisks"))
            range_var = num_disks + 1
            for diskNum in range(1, range_var):
                data_dirs.append(self.get("azure", "mount_root") +
                                 str(diskNum))

        return data_dirs

    def worker_data_dirs(self):
        return self.data_dirs_common("worker")

    def default_data_dirs(self):
        return self.data_dirs_common("default")

    def metrics_drive_ids(self):
        if self.get_cluster_type() == 'ec2':
            drive_ids = []
            for i in range(0, self.max_ephemeral()):
                drive_ids.append(self.metrics_drive_root + str(i))
            return drive_ids
        elif self.get_cluster_type() == 'existing':
            return self.get("existing", "metrics_drive_ids").split(",")
        elif self.get_cluster_type() == 'azure':
            drive_ids = []
            range_var = int(self.get("azure", "numdisks")) + 1
            for i in range(1, range_var):
                drive_ids.append(self.get("azure", "metrics_drive_root") +
                                 str(i))
            return drive_ids

    def shutdown_delay_minutes(self):
        retval = '0'
        if self.get_cluster_type() == 'ec2':
            retval = self.get("ec2", "shutdown_delay_minutes")
        return retval

    def version(self, software_id):
        return self.get('general', software_id + '_version')

    def checksum(self, software):
        return self.checksum_ver(software, self.version(software))

    def checksum_ver(self, software, version):
        if not os.path.isfile(self.checksums_path):
            exit('ERROR - A checksums file does not exist at %s' % self.hosts_path)

        if "SNAPSHOT" in version:
            return ""

        if not self.checksums_d:
            self.checksums_d = {}
            with open(self.checksums_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue
                    args = line.split(':')
                    if len(args) == 3:
                        self.checksums_d["{0}:{1}".format(args[0], args[1])] = args[2]
                    else:
                        exit('ERROR - Bad line %s in checksums %s' % (line, self.checksums_path))

        key = "{0}:{1}".format(software, version)
        if key not in self.checksums_d:
            exit('ERROR - Failed to find checksums for %s %s in %s' % (software, version, self.checksums_path))
        return self.checksums_d[key]

    def verify_instance_type(self, instance_type):
        if not self.cluster_template_d:
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
        for (hostname, service_list) in list(self.node_d.items()):
            if service in service_list:
                return True
        return False

    def get_host_services(self):
        retval = []
        for (hostname, service_list) in list(self.node_d.items()):
            retval.append((hostname, ' '.join(service_list)))
        retval.sort()
        return retval

    def get_service_private_ips(self, service):
        retval = []
        for (hostname, service_list) in list(self.node_d.items()):
            if service in service_list:
                retval.append(self.get_private_ip(hostname))
        retval.sort()
        return retval

    def get_service_hostnames(self, service):
        retval = []
        for (hostname, service_list) in list(self.node_d.items()):
            if service in service_list:
                retval.append(hostname)
        retval.sort()
        return retval

    def get_non_proxy(self):
        retval = []
        proxy_ip = self.get_private_ip(self.get('general', 'proxy_hostname'))
        for (hostname, (private_ip, public_ip)) in list(self.get_hosts().items()):
            if private_ip != proxy_ip:
                retval.append((private_ip, hostname))
        retval.sort()
        return retval

    def get_private_ip_hostnames(self):
        retval = []
        for (hostname, (private_ip, public_ip)) in list(self.get_hosts().items()):
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

    def get_cluster_type(self):
        if self.cluster_type not in ('azure', 'ec2', 'existing'):
            exit('ERROR - Unknown cluster type' + self.cluster_type)
        return self.cluster_type

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
        print('proxy_public_ip = ', self.proxy_public_ip())
        for (name, val) in self.items('general'):
            print(name, '=', val)

        for (name, val) in self.items('ec2'):
            print(name, '=', val)

        for (name, val) in self.items('azure'):
            print(name, '=', val)

    def print_property(self, key):
        if key == 'proxy.public.ip':
            print(self.proxy_public_ip())
            return
        else:
            for section in self.sections():
                if self.has_option(section, key):
                    print(self.get(section, key))
                    return
        exit("Property '{0}' was not found".format(key))

    def init_template(self, templates_path):
        if self.has_option('ec2', 'cluster_template'):
            template_id = self.get('ec2', 'cluster_template')
            template_path = os.path.join(templates_path, template_id)
            if os.path.exists(template_path):
                self.cluster_template_d = {'id': template_id}
                self.load_template_ec2_requests(template_path)
                self.load_template_device_map(template_path)
            self.validate_template()

    def load_template_ec2_requests(self, template_dir):
        for json_path in glob.glob(os.path.join(template_dir, '*.json')):
            service = os.path.basename(json_path).rsplit('.', 1)[0]
            if service not in SERVICES:
                exit("ERROR - Template '{0}' has unrecognized option '{1}'. Must be one of {2}".format(
                    self.cluster_template_d['id'], service, str(SERVICES)))
            with open(json_path, 'r') as json_file:
                # load as string, so we can use string.Template to inject config values
                self.cluster_template_d[service] = json_file.read()

    def load_template_device_map(self, template_dir):
        device_map_path = os.path.join(template_dir, 'devices')
        if not os.path.isfile(device_map_path):
            exit("ERROR - template '{0}' is missing 'devices' config".format(self.cluster_template_d['id']))
        with open(device_map_path, 'r') as json_file:
            self.cluster_template_d['devices'] = json.load(json_file)

    def validate_template(self):
        if not self.cluster_template_d:
            exit("ERROR - Template '{0}' is not defined!".format(self.get('ec2', 'cluster_template')))

        if 'worker' not in self.cluster_template_d:
            exit("ERROR - '{0}' template config is invalid. No 'worker' launch request is defined".format(
                self.cluster_template_d['id']))

        if 'worker' not in self.cluster_template_d['devices']:
            exit("ERROR - '{0}' template is invalid. The devices file must have a 'worker' device map".format(
                self.cluster_template_d['id']))

        if 'default' not in self.cluster_template_d['devices']:
            exit("ERROR - '{0}' template is invalid. The devices file must have a 'default' device map".format(
                self.cluster_template_d['id']))

        # Validate the selected launch template for each host

        worker_count = 0
        for hostname in self.node_d:
            # first service listed denotes the selected template
            selected_ec2_request = self.node_d[hostname][0]
            if 'worker' == selected_ec2_request:
                worker_count = worker_count + 1
            else:
                if 'worker' in self.node_d[hostname]:
                    exit("ERROR - '{0}' node config is invalid. The 'worker' service should be listed first".format(
                        hostname))
            if selected_ec2_request not in self.cluster_template_d:
                if len(self.node_d[hostname]) > 1:
                    print('Hint: In template mode, the first service listed for a host denotes its EC2 template')
                exit("ERROR - '{0}' node config is invalid. No EC2 template defined for the '{1}' service".format(
                    hostname, selected_ec2_request))

        if worker_count == 0:
            exit("ERROR - No worker instances are defined for template '{0}'".format(self.cluster_template_d['id']))


HOST_VAR_DEFAULTS = {
  'accumulo_home': '"{{ install_dir }}/accumulo-{{ accumulo_version }}"',
  'accumulo_instance': None,
  'accumulo_major_version': '"{{ accumulo_version.split(\'.\')[0] }}"',
  'accumulo_password': None,
  'accumulo_tarball': 'accumulo-{{ accumulo_version }}-bin.tar.gz',
  'accumulo_version': None,
  'cluster_type': None,
  'cluster_group': None,
  'cluster_user': None,
  'default_data_dirs': None,
  'download_software': None,
  'fluo_home': '"{{ install_dir }}/fluo-{{ fluo_version }}"',
  'fluo_tarball': 'fluo-{{ fluo_version }}-bin.tar.gz',
  'fluo_version': None,
  'fluo_yarn_home': '"{{ install_dir }}/fluo-yarn-{{ fluo_yarn_version }}"',
  'fluo_yarn_tarball': 'fluo-yarn-{{ fluo_yarn_version }}-bin.tar.gz',
  'fluo_yarn_version': None,
  'hadoop_home': '"{{ install_dir }}/hadoop-{{ hadoop_version }}"',
  'hadoop_tarball': 'hadoop-{{ hadoop_version }}.tar.gz',
  'hadoop_version': None,
  'hadoop_major_version': '"{{ hadoop_version.split(\'.\')[0] }}"',
  'hdfs_root': "{% if hdfs_ha %}hdfs://{{ nameservice_id }}{% else %}hdfs://{{ groups[\'namenode\'][0] }}:8020{% endif %}",
  'hdfs_ha': None,
  'nameservice_id': None,
  'install_dir': None,
  'install_hub': None,
  'java_home': '"/usr/lib/jvm/java"',
  'java_package': '"java-1.8.0-openjdk-devel"',
  'journal_quorum': "{% for host in groups['journalnode'] %}{{ host }}:8485{% if not loop.last %};{% endif %}{% endfor %}",
  'maven_home': '"{{ install_dir }}/apache-maven-{{ maven_version }}"',
  'maven_tarball': 'apache-maven-{{ maven_version }}-bin.tar.gz',
  'maven_version': '3.6.3',
  'spark_home': '"{{ install_dir }}/spark-{{ spark_version }}-bin-without-hadoop"',
  'spark_tarball': 'spark-{{ spark_version }}-bin-without-hadoop.tgz',
  'spark_version': None,
  'tarballs_dir': '"{{ user_home }}/tarballs"',
  'user_home': None,
  'worker_data_dirs': None,
  'zookeeper_connect': "{% for host in groups['zookeepers'] %}{{ host }}:2181{% if not loop.last %},{% endif %}{% endfor %}",
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
  'fluo_sha256': None,
  'fluo_worker_instances_multiplier': None,
  'fluo_worker_mem_mb': None,
  'fluo_worker_threads': None,
  'fluo_yarn_sha256': None,
  'force_format': None,
  'fstype': None,
  'hadoop_sha256': None,
  'hub_version': '2.2.3',
  'hub_home': '"{{ install_dir }}/hub-linux-amd64-{{ hub_version }}"',
  'hub_tarball': 'hub-linux-amd64-{{ hub_version }}.tgz',
  'hub_sha256': '54c35a459a4241b7ae4c28bcfea0ceef849dd2f8a9dd2b82ba2ba964a743e6bc',
  'maven_sha256': '26ad91d751b3a9a53087aefa743f4e16a17741d3915b219cf74112bf87a438c5',
  'metrics_drive_ids': None,
  'mount_root': None,
  'node_type_map': None,
  'spark_sha256': None,
  'shutdown_delay_minutes': None,
  'twill_reserve_mem_mb': None,
  'yarn_nm_mem_mb': None,
  'zookeeper_sha256': None
}

AZURE_VAR_DEFAULTS = {
  'azure_fileshare_mount': None,
  'azure_fileshare': None,
  'azure_fileshare_username': None,
  'azure_fileshare_password': None,
  'az_omsIntegrationNeeded': None,
  'az_logs_id': None,
  'az_logs_key': None
}
