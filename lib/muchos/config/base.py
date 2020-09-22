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

from abc import ABCMeta, abstractmethod
from collections import ChainMap
from configparser import ConfigParser
from distutils.version import StrictVersion
from os.path import isfile
from sys import exit
from .decorators import (
    ansible_host_var,
    ansible_play_var,
    get_ansible_vars,
    is_valid,
)
from .validators import is_in

SERVICES = [
    "zookeeper",
    "namenode",
    "resourcemanager",
    "accumulomaster",
    "mesosmaster",
    "worker",
    "fluo",
    "fluo_yarn",
    "metrics",
    "spark",
    "client",
    "swarmmanager",
    "journalnode",
    "zkfc",
    "elkserver",
]

OPTIONAL_SERVICES = [
    "fluo",
    "fluo_yarn",
    "metrics",
    "mesosmaster",
    "spark",
    "client",
    "swarmmanager",
    "journalnode",
    "zkfc",
    "elkserver",
]

_HOST_VAR_DEFAULTS = {
    "accumulo_home": "'{{ install_dir }}/accumulo-{{ accumulo_version }}'",
    "accumulo_instance": None,
    "accumulo_major_version": "{{ accumulo_version.split('.')[0] }}",
    "accumulo_password": None,
    "accumulo_tarball": "accumulo-{{ accumulo_version }}-bin.tar.gz",
    "accumulo_version": None,
    "cluster_type": None,
    "cluster_group": None,
    "cluster_user": None,
    "default_data_dirs": None,
    "download_software": None,
    "fluo_home": "'{{ install_dir }}/fluo-{{ fluo_version }}'",
    "fluo_tarball": "fluo-{{ fluo_version }}-bin.tar.gz",
    "fluo_version": None,
    "fluo_yarn_home": "'{{ install_dir }}/fluo-yarn-{{ fluo_yarn_version }}'",
    "fluo_yarn_tarball": "fluo-yarn-{{ fluo_yarn_version }}-bin.tar.gz",
    "fluo_yarn_version": None,
    "hadoop_home": "'{{ install_dir }}/hadoop-{{ hadoop_version }}'",
    "hadoop_tarball": "hadoop-{{ hadoop_version }}.tar.gz",
    "hadoop_version": None,
    "hadoop_major_version": "{{ hadoop_version.split('.')[0] }}",
    "hdfs_root": "hdfs://{{ nameservice_id }}",
    "hdfs_ha": None,
    "nameservice_id": None,
    "num_tservers": 1,
    "install_dir": None,
    "install_hub": None,
    "java_home": "/usr/lib/jvm/java",
    "java_package": "java-1.8.0-openjdk-devel",
    "journal_quorum": (
        "{% for host in groups['journalnode'] %}{{ host }}"
        ":8485{% if not loop.last %};{% endif %}{% endfor %}"
    ),
    "maven_home": "{{ install_dir }}/apache-maven-{{ maven_version }}",
    "maven_tarball": "apache-maven-{{ maven_version }}-bin.tar.gz",
    "maven_version": "3.6.3",
    "spark_home": (
        "'{{ install_dir }}/spark-{{ spark_version }}" "-bin-without-hadoop'"
    ),
    "spark_tarball": "spark-{{ spark_version }}-bin-without-hadoop.tgz",
    "spark_version": None,
    "tarballs_dir": "'{{ user_home }}/tarballs'",
    "user_home": None,
    "worker_data_dirs": None,
    "zookeeper_connect": (
        "{% for host in groups['zookeepers'] %}{{ host }}"
        ":2181{% if not loop.last %},{% endif %}{% endfor %}"
    ),
    "zookeeper_client_port": "2181",
    "zookeeper_basename": (
        "{% if zookeeper_version is version('3.5', '>=') or "
        "zookeeper_version in 'SNAPSHOT' %}"
        "apache-zookeeper-{{ zookeeper_version }}-bin{% else %}"
        "zookeeper-{{ zookeeper_version }}{% endif %}"
    ),
    "zookeeper_home": "{{ install_dir }}/{{ zookeeper_basename }}",
    "zookeeper_tarball": "{{ zookeeper_basename }}.tar.gz",
    "zookeeper_version": None,
}

_PLAY_VAR_DEFAULTS = {
    "accumulo_dcache_size": None,
    "accumulo_icache_size": None,
    "accumulo_imap_size": None,
    "accumulo_checksum": None,
    "accumulo_tserv_mem": None,
    "fluo_checksum": None,
    "fluo_worker_instances_multiplier": None,
    "fluo_worker_mem_mb": None,
    "fluo_worker_threads": None,
    "fluo_yarn_checksum": None,
    "hadoop_checksum": None,
    "hub_version": "2.2.3",
    "hub_home": '"{{ install_dir }}/hub-linux-amd64-{{ hub_version }}"',
    "hub_tarball": "hub-linux-amd64-{{ hub_version }}.tgz",
    "hub_checksum": (
        "sha256:"
        "54c35a459a4241b7ae4c28bcfea0ceef849dd2f8a9dd2b82ba2ba964a743e6bc"
    ),
    "maven_checksum": (
        "sha512:"
        "c35a1803a6e70a126e80b2b3ae33eed961f83ed74d18fcd16909b2d44d7dada3203f1ffe726c17ef8dcca2dcaa9fca676987befeadc9b9f759967a8cb77181c0"  # noqa
    ),
    "metrics_drive_ids": None,
    "mount_root": None,
    "node_type_map": None,
    "spark_checksum": None,
    "shutdown_delay_minutes": None,
    "twill_reserve_mem_mb": None,
    "yarn_nm_mem_mb": None,
    "zookeeper_checksum": None,
    "use_systemd": False,
}

_EXTRA_VAR_DEFAULTS = {}

HASHLEN_ALGO_MAP = {
    32: "md5",
    40: "sha1",
    56: "sha224",
    64: "sha256",
    96: "sha384",
    128: "sha512",
}


class BaseConfig(ConfigParser, metaclass=ABCMeta):
    def __init__(
        self,
        deploy_path,
        config_path,
        hosts_path,
        checksums_path,
        templates_path,
        cluster_name,
    ):
        super(BaseConfig, self).__init__()
        self.optionxform = str
        self.deploy_path = deploy_path
        self.read(config_path)
        self.hosts_path = hosts_path
        self.cluster_name = cluster_name
        self.cluster_type = self.get("general", "cluster_type")
        self.node_d = None
        self.hosts = None
        self.checksums_path = checksums_path
        self.checksums_d = None
        self._init_nodes()

    def ansible_host_vars(self):
        return dict(
            ChainMap(
                self._ansible_vars_from_decorators("host"),
                getattr(self, "HOST_VAR_DEFAULTS", {}),
                _HOST_VAR_DEFAULTS,
            )
        )

    def ansible_play_vars(self):
        software_checksums = {
            "{}_checksum".format(k): self.checksum(k)
            for k in [
                "accumulo",
                "fluo",
                "fluo_yarn",
                "hadoop",
                "spark",
                "zookeeper",
            ]
        }
        return dict(
            ChainMap(
                self._ansible_vars_from_decorators("play"),
                software_checksums,
                getattr(self, "PLAY_VAR_DEFAULTS", {}),
                _PLAY_VAR_DEFAULTS,
            )
        )

    def ansible_extra_vars(self):
        return dict(
            ChainMap(
                self._ansible_vars_from_decorators("extra"),
                getattr(self, "EXTRA_VAR_DEFAULTS", {}),
                _EXTRA_VAR_DEFAULTS,
            )
        )

    def _ansible_vars_from_decorators(self, var_type):
        # only render play_vars for base and cluster specific config
        f = ["{}deployconfig".format(self.get_cluster_type()), "baseconfig"]
        return {
            v.var_name: getattr(self, v.property_name)()
            for v in
            # filter out any classes that are not baseconfig or
            # the cluster specific config
            filter(
                lambda t: t.class_name.lower() in f,
                # get all ansible vars of var_type
                get_ansible_vars(var_type, type(self)),
            )
        }

    @abstractmethod
    def verify_config(self, action):
        raise NotImplementedError()

    # helper for verify_config to call for common checks
    def _verify_config(self, action):
        if action in ["launch", "setup"]:
            for service in SERVICES:
                if service not in OPTIONAL_SERVICES:
                    if not self.has_service(service):
                        exit(
                            "ERROR - Missing '{0}' service from [nodes] "
                            "section of muchos.props".format(service)
                        )

            # fail if we are using Java 11 along with Accumulo 1.x
            # See https://github.com/apache/accumulo/issues/958 for details
            if self.java_product_version() >= 11 and StrictVersion(
                self.version("accumulo").replace("-SNAPSHOT", "")
            ) <= StrictVersion("1.9.3"):
                exit(
                    "ERROR - Java 11 is not supported with Accumulo version "
                    "'{0}'".format(self.version("accumulo"))
                )

            # fail if we are using ZooKeeper >= 3.5.5 with Accumulo <= 1.9.x
            if StrictVersion(
                self.version("zookeeper").replace("-SNAPSHOT", "")
            ) >= StrictVersion("3.5.5") and StrictVersion(
                self.version("accumulo").replace("-SNAPSHOT", "")
            ) < StrictVersion(
                "1.10.0"
            ):
                exit(
                    "ERROR - ZooKeeper version '{0}' is not supported with "
                    "Accumulo version '{1}'".format(
                        self.version("zookeeper"), self.version("accumulo")
                    )
                )

    @abstractmethod
    def verify_launch(self):
        raise NotImplementedError()

    def _init_nodes(self):
        self.node_d = {}
        for (hostname, value) in self.items("nodes"):
            if hostname in self.node_d:
                exit(
                    "Hostname {0} already exists twice in nodes".format(
                        hostname
                    )
                )
            service_list = []
            for service in value.split(","):
                if service in SERVICES:
                    service_list.append(service)
                else:
                    exit(
                        "Unknown service '{}' declared for node {}".format(
                            service, hostname
                        )
                    )
            self.node_d[hostname] = service_list

    @abstractmethod
    @ansible_play_var
    def node_type_map(self):
        raise NotImplementedError()

    @is_valid(is_in(["default", "worker"]))
    def node_type(self, hostname):
        if "worker" in self.node_d[hostname]:
            return "worker"
        return "default"

    def user_home(self):
        return self.get("general", "user_home")

    def mounts(self, num_ephemeral):
        mounts = []
        for i in range(0, num_ephemeral):
            mounts.append(self.mount_root() + str(i))
        return mounts

    @abstractmethod
    @ansible_play_var
    def mount_root(self):
        raise NotImplementedError()

    @abstractmethod
    def data_dirs_common(self, nodeType):
        raise NotImplementedError()

    @ansible_host_var
    def worker_data_dirs(self):
        return self.data_dirs_common("worker")

    @ansible_host_var
    def default_data_dirs(self):
        return self.data_dirs_common("default")

    @abstractmethod
    @ansible_play_var
    def metrics_drive_ids(self):
        raise NotImplementedError()

    @ansible_play_var
    def shutdown_delay_minutes(self):
        return "0"

    def version(self, software_id):
        return self.get("general", software_id + "_version")

    def filter_by_java_version(self, dict_to_search):
        # Given that a user might chose to install a specific JDK version
        # (where the version is suffixed to package name) it is safer
        # to check if the configured Java version starts with one of the above
        # prefixes defined in the version map
        configured_java_version = self.get("general", "java_package")
        filtered_java_versions = {
            k: v
            for (k, v) in dict_to_search.items()
            if configured_java_version.startswith(k)
        }
        if len(filtered_java_versions) != 1:
            exit(
                "ERROR - unknown or ambiguous Java version '{0}' specified"
                " in properties".format(configured_java_version)
            )

        return next(iter(filtered_java_versions.values()))

    @ansible_host_var
    def java_product_version(self):
        java_version_map = {
            "java-1.8.0-openjdk": 8,
            "java-11-openjdk": 11,
            "java-latest-openjdk": 14,
        }

        return self.filter_by_java_version(java_version_map)

    @ansible_host_var
    def jdk_folder_pattern(self):
        jdk_folder_pattern_map = {
            "java-1.8.0-openjdk": "java-1.8.0-openjdk*x86_64",
            "java-11-openjdk": "java-11-openjdk*x86_64",
            "java-latest-openjdk": "java-14-openjdk*x86_64",
        }

        return self.filter_by_java_version(jdk_folder_pattern_map)

    def checksum(self, software):
        return self.checksum_ver(software, self.version(software))

    def infer_hash_algo(self, hashstring):
        # infer the algorithm based on length
        hashlen = len(hashstring)

        if hashlen in HASHLEN_ALGO_MAP:
            return HASHLEN_ALGO_MAP[hashlen]
        else:
            return None

    def checksum_ver(self, software, version):
        if not isfile(self.checksums_path):
            exit(
                "ERROR - A checksums file does not exist at {}".format(
                    self.hosts_path
                )
            )

        if "SNAPSHOT" in version:
            return ""

        if not self.checksums_d:
            self.checksums_d = {}
            with open(self.checksums_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue
                    args = line.split(":")
                    if len(args) == 3:
                        inferred_algo = self.infer_hash_algo(args[2])
                        if inferred_algo is not None:
                            self.checksums_d[
                                "{0}:{1}".format(args[0], args[1])
                            ] = "{0}:{1}".format(
                                self.infer_hash_algo(args[2]), args[2]
                            )
                        else:
                            exit(
                                "ERROR - Bad line {} in checksums {}".format(
                                    line, self.checksums_path
                                )
                            )

                    elif len(args) == 4:
                        if args[2] not in HASHLEN_ALGO_MAP.values():
                            exit(
                                "ERROR - Unsupported hash algorithm {} "
                                "in checksums {}".format(
                                    line, self.checksums_path
                                )
                            )
                        self.checksums_d[
                            "{0}:{1}".format(args[0], args[1])
                        ] = "{0}:{1}".format(args[2], args[3])
                    else:
                        exit(
                            "ERROR - Bad line {} in checksums {}".format(
                                line, self.checksums_path
                            )
                        )

        key = "{0}:{1}".format(software, version)
        if key not in self.checksums_d:
            exit(
                "ERROR - Failed to find checksums for {} {} in {}".format(
                    software, version, self.checksums_path
                )
            )
        return self.checksums_d[key]

    def nodes(self):
        return self.node_d

    def get_node(self, hostname):
        return self.node_d[hostname]

    def has_service(self, service):
        for (hostname, service_list) in list(self.node_d.items()):
            if service in service_list:
                return True
        return False

    # test method, might want to make private or just move to test module
    def get_host_services(self):
        retval = []
        for (hostname, service_list) in list(self.node_d.items()):
            retval.append((hostname, " ".join(service_list)))
        retval.sort()
        return retval

    # test method, might want to make private or just move to test module
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

    # test method, might want to make private or just move to test module
    def get_non_proxy(self):
        retval = []
        proxy_ip = self.get_private_ip(self.get("general", "proxy_hostname"))
        for (hostname, (private_ip, public_ip)) in list(
            self.get_hosts().items()
        ):
            if private_ip != proxy_ip:
                retval.append((private_ip, hostname))
        retval.sort()
        return retval

    def get_private_ip_hostnames(self):
        retval = []
        for (hostname, (private_ip, public_ip)) in list(
            self.get_hosts().items()
        ):
            retval.append((private_ip, hostname))
        retval.sort()
        return retval

    def parse_hosts(self):
        if not isfile(self.hosts_path):
            exit(
                "ERROR - A hosts file does not exist at {}".format(
                    self.hosts_path
                )
            )

        self.hosts = {}
        with open(self.hosts_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                args = line.split(" ")
                if len(args) == 2:
                    self.hosts[args[0]] = (args[1], None)
                elif len(args) == 3:
                    self.hosts[args[0]] = (args[1], args[2])
                else:
                    exit(
                        "ERROR - Bad line {} in hosts {}".format(
                            line, self.hosts_path
                        )
                    )

    def get_hosts(self):
        if self.hosts is None:
            self.parse_hosts()
        return self.hosts

    def get_private_ip(self, hostname):
        return self.get_hosts()[hostname][0]

    def get_public_ip(self, hostname):
        return self.get_hosts()[hostname][1]

    def get_cluster_type(self):
        if self.cluster_type not in ("azure", "ec2", "existing"):
            exit("ERROR - Unknown cluster type" + self.cluster_type)
        return self.cluster_type

    def proxy_hostname(self):
        return self.get("general", "proxy_hostname")

    def proxy_public_ip(self):
        retval = self.get_public_ip(self.proxy_hostname())
        if not retval:
            exit(
                "ERROR - Proxy '{0}' does not have a public IP".format(
                    self.proxy_hostname()
                )
            )
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
        profile = self.get("performance", "profile")
        return self.get(profile, prop)

    def print_all(self):
        print("proxy_public_ip = ", self.proxy_public_ip())
        for (name, val) in self.items("general"):
            print(name, "=", val)

        for (name, val) in self.items("ec2"):
            print(name, "=", val)

        for (name, val) in self.items("azure"):
            print(name, "=", val)

    def print_property(self, key):
        if key == "proxy.public.ip":
            print(self.proxy_public_ip())
            return
        else:
            for section in self.sections():
                if self.has_option(section, key):
                    print(self.get(section, key))
                    return
        exit("Property '{0}' was not found".format(key))

    def resolve_value(self, config_name, default=None):
        # listed low to high priority
        section_priority = [
            "general",
            "ansible-vars",
            self.get("performance", "profile"),
        ]
        all_values = [
            self.get(section, config_name, fallback=None)
            for section in section_priority
        ]
        try:
            *_, val = filter(None, all_values)
        except ValueError:
            return default
        return val
