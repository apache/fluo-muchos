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

import shutil
import subprocess
import time
from os import path
from sys import exit
from os import listdir


class ExistingCluster:
    def __init__(self, config):
        self.config = config

    def launch(self):
        exit(
            "ERROR - 'launch' command cannot be used "
            "when cluster_type is set to 'existing'"
        )

    def sync(self):
        config = self.config
        print(
            "Syncing ansible directory on {0} cluster proxy node".format(
                config.cluster_name
            )
        )

        host_vars = config.ansible_host_vars()
        play_vars = config.ansible_play_vars()

        for k, v in host_vars.items():
            host_vars[k] = self.config.resolve_value(k, default=v)
        for k, v in play_vars.items():
            play_vars[k] = self.config.resolve_value(k, default=v)

        with open(
            path.join(config.deploy_path, "ansible/site.yml"), "w"
        ) as site_file:
            print("- import_playbook: common.yml", file=site_file)

            print("- import_playbook: zookeeper.yml", file=site_file)
            print("- import_playbook: hadoop.yml", file=site_file)

            if config.has_service("spark"):
                print("- import_playbook: spark.yml", file=site_file)

            if config.has_service("metrics"):
                print("- import_playbook: metrics.yml", file=site_file)
            print("- import_playbook: accumulo.yml", file=site_file)
            if config.has_service("fluo"):
                print("- import_playbook: fluo.yml", file=site_file)
            if config.has_service("fluo_yarn"):
                print("- import_playbook: fluo_yarn.yml", file=site_file)
            if config.has_service("mesosmaster"):
                print("- import_playbook: mesos.yml", file=site_file)
            if config.has_service("swarmmanager"):
                print("- import_playbook: docker.yml", file=site_file)
            if config.has_service("elkserver"):
                print("- import_playbook: elk.yml", file=site_file)

        ansible_conf = path.join(config.deploy_path, "ansible/conf")
        with open(path.join(ansible_conf, "hosts"), "w") as hosts_file:
            print(
                "[proxy]\n{0}".format(config.proxy_hostname()), file=hosts_file
            )
            print("\n[accumulomaster]", file=hosts_file)
            for accu_host in config.get_service_hostnames("accumulomaster"):
                print(accu_host, file=hosts_file)
            print("\n[namenode]", file=hosts_file)
            for nn_host in config.get_service_hostnames("namenode"):
                print(nn_host, file=hosts_file)
            print("\n[journalnode]", file=hosts_file)
            for jn_host in config.get_service_hostnames("journalnode"):
                print(jn_host, file=hosts_file)
            print("\n[zkfc]", file=hosts_file)
            for zkfc_host in config.get_service_hostnames("zkfc"):
                print(zkfc_host, file=hosts_file)
            print("\n[resourcemanager]", file=hosts_file)
            for rm_host in config.get_service_hostnames("resourcemanager"):
                print(rm_host, file=hosts_file)
            if config.has_service("spark"):
                print(
                    "\n[spark]\n{0}".format(
                        config.get_service_hostnames("spark")[0]
                    ),
                    file=hosts_file,
                )
            if config.has_service("mesosmaster"):
                print(
                    "\n[mesosmaster]\n{0}".format(
                        config.get_service_hostnames("mesosmaster")[0]
                    ),
                    file=hosts_file,
                )
            if config.has_service("metrics"):
                print(
                    "\n[metrics]\n{0}".format(
                        config.get_service_hostnames("metrics")[0]
                    ),
                    file=hosts_file,
                )
            if config.has_service("swarmmanager"):
                print(
                    "\n[swarmmanager]\n{0}".format(
                        config.get_service_hostnames("swarmmanager")[0]
                    ),
                    file=hosts_file,
                )

            if config.has_service("elkserver"):
                print(
                    "\n[elkserver]\n{0}".format(
                        config.get_service_hostnames("elkserver")[0]
                    ),
                    file=hosts_file,
                )

            print("\n[zookeepers]", file=hosts_file)
            for (index, zk_host) in enumerate(
                config.get_service_hostnames("zookeeper"), start=1
            ):
                print("{0} id={1}".format(zk_host, index), file=hosts_file)

            if config.has_service("fluo"):
                print("\n[fluo]", file=hosts_file)
                for host in config.get_service_hostnames("fluo"):
                    print(host, file=hosts_file)

            if config.has_service("fluo_yarn"):
                print("\n[fluo_yarn]", file=hosts_file)
                for host in config.get_service_hostnames("fluo_yarn"):
                    print(host, file=hosts_file)

            print("\n[workers]", file=hosts_file)
            for worker_host in config.get_service_hostnames("worker"):
                print(worker_host, file=hosts_file)

            print(
                "\n[accumulo:children]\naccumulomaster\nworkers",
                file=hosts_file,
            )
            print(
                "\n[hadoop:children]\nnamenode\nresourcemanager"
                "\nworkers\nzkfc\njournalnode",
                file=hosts_file,
            )

            print("\n[nodes]", file=hosts_file)
            for (private_ip, hostname) in config.get_private_ip_hostnames():
                print(
                    "{0} ansible_ssh_host={1} node_type={2}".format(
                        hostname, private_ip, config.node_type(hostname)
                    ),
                    file=hosts_file,
                )

            print("\n[all:vars]", file=hosts_file)
            for (name, value) in sorted(host_vars.items()):
                print("{0} = {1}".format(name, value), file=hosts_file)

        with open(
            path.join(config.deploy_path, "ansible/group_vars/all"), "w"
        ) as play_vars_file:
            for (name, value) in sorted(play_vars.items()):
                print("{0}: {1}".format(name, value), file=play_vars_file)

        # copy keys file to ansible/conf (if it exists)
        conf_keys = path.join(config.deploy_path, "conf/keys")
        ansible_keys = path.join(ansible_conf, "keys")
        if path.isfile(conf_keys):
            shutil.copyfile(conf_keys, ansible_keys)
        else:
            open(ansible_keys, "w").close()

        cmd = "rsync -az --delete -e \"ssh -o 'StrictHostKeyChecking no'\""
        subprocess.call(
            "{cmd} {src} {usr}@{ldr}:{tdir}".format(
                cmd=cmd,
                src=path.join(config.deploy_path, "ansible"),
                usr=config.get("general", "cluster_user"),
                ldr=config.get_proxy_ip(),
                tdir=config.user_home(),
            ),
            shell=True,
        )

        self.exec_on_proxy_verified(
            "{0}/ansible/scripts/install_ansible.sh".format(
                config.user_home()
            ),
            opts="-t",
        )

    def setup(self):
        config = self.config
        print("Setting up {0} cluster".format(config.cluster_name))

        self.sync()

        conf_upload = path.join(config.deploy_path, "conf/upload")
        cluster_tarballs = "{0}/tarballs".format(config.user_home())
        self.exec_on_proxy_verified("mkdir -p {0}".format(cluster_tarballs))
        for f in listdir(conf_upload):
            tarball_path = path.join(conf_upload, f)
            if path.isfile(tarball_path) and tarball_path.endswith("gz"):
                self.send_to_proxy(tarball_path, cluster_tarballs)

        self.execute_playbook("site.yml")

    @staticmethod
    def status():
        exit(
            "ERROR - 'status' command cannot be used "
            "when cluster_type is set to 'existing'"
        )

    @staticmethod
    def terminate():
        exit(
            "ERROR - 'terminate' command cannot be used "
            "when cluster_type is set to 'existing'"
        )

    @staticmethod
    def stop():
        exit(
            "ERROR - 'stop' command cannot be used "
            "when cluster_type is set to 'existing'"
        )

    @staticmethod
    def start():
        exit(
            "ERROR - 'start' command cannot be used "
            "when cluster_type is set to 'existing'"
        )

    def ssh(self):
        self.wait_until_proxy_ready()
        fwd = ""
        if self.config.has_option("general", "proxy_socks_port"):
            fwd = "-D " + self.config.get("general", "proxy_socks_port")
        ssh_command = (
            "ssh -C -A -o 'StrictHostKeyChecking no' " "{fwd} {usr}@{ldr}"
        ).format(
            usr=self.config.get("general", "cluster_user"),
            ldr=self.config.get_proxy_ip(),
            fwd=fwd,
        )
        print("Logging into proxy using: {0}".format(ssh_command))
        retcode = subprocess.call(ssh_command, shell=True)
        if retcode != 0:
            exit(
                "ERROR - Command failed with return code of {0}: {1}".format(
                    retcode, ssh_command
                )
            )

    def exec_on_proxy(self, command, opts=""):
        ssh_command = (
            "ssh -A -o 'StrictHostKeyChecking no' "
            "{opts} {usr}@{ldr} '{cmd}'"
        ).format(
            usr=self.config.get("general", "cluster_user"),
            ldr=self.config.get_proxy_ip(),
            cmd=command,
            opts=opts,
        )
        return subprocess.call(ssh_command, shell=True), ssh_command

    def exec_on_proxy_verified(self, command, opts=""):
        (retcode, ssh_command) = self.exec_on_proxy(command, opts)
        if retcode != 0:
            exit(
                "ERROR - Command failed with return code of {0}: {1}".format(
                    retcode, ssh_command
                )
            )

    def wait_until_proxy_ready(self):
        cluster_user = self.config.get("general", "cluster_user")
        print(
            "Checking if '{0}' proxy can be reached using: "
            "ssh {1}@{2}".format(
                self.config.proxy_hostname(),
                cluster_user,
                self.config.get_proxy_ip(),
            )
        )
        while True:
            (retcode, ssh_command) = self.exec_on_proxy("pwd > /dev/null")
            if retcode == 0:
                print("Connected to proxy using SSH!")
                time.sleep(1)
                break
            print(
                "Proxy could not be accessed using SSH. "
                "Will retry in 5 sec..."
            )
            time.sleep(5)

    def execute_playbook(self, playbook):
        print("Executing '{0}' playbook".format(playbook))
        azure_proxy_host = self.config.get("azure", "azure_proxy_host")
        var_azure_proxy_host = (
            "_"
            if (azure_proxy_host is None or azure_proxy_host.strip() == "")
            else azure_proxy_host
        )
        self.exec_on_proxy_verified(
            "time -p ansible-playbook {base}/ansible/{playbook} "
            "--extra-vars 'azure_proxy_host={var_azure_proxy_host}'".format(
                base=self.config.user_home(),
                playbook=playbook,
                var_azure_proxy_host=var_azure_proxy_host,
            ),
            opts="-t",
        )

    def send_to_proxy(self, path, target, skip_if_exists=True):
        print("Copying to proxy: ", path)
        cmd = "scp -o 'StrictHostKeyChecking no'"
        if skip_if_exists:
            cmd = (
                'rsync --update --progress -e "ssh -q -o '
                "'StrictHostKeyChecking no'\""
            )
        subprocess.call(
            "{cmd} {src} {usr}@{ldr}:{tdir}".format(
                cmd=cmd,
                src=path,
                usr=self.config.get("general", "cluster_user"),
                ldr=self.config.get_proxy_ip(),
                tdir=target,
            ),
            shell=True,
        )

    def wipe(self):
        if not path.isfile(self.config.hosts_path):
            exit(
                "Hosts file does not exist for cluster: "
                + self.config.hosts_path
            )
        print(
            "Killing all processes started by Muchos and "
            "wiping Muchos data from {0} cluster".format(
                self.config.cluster_name
            )
        )
        self.execute_playbook("wipe.yml")

    def perform(self, action):
        if action == "launch":
            self.launch()
        elif action == "status":
            self.status()
        elif action == "sync":
            self.sync()
        elif action == "setup":
            self.setup()
        elif action == "start":
            self.start()
        elif action == "stop":
            self.stop()
        elif action == "ssh":
            self.ssh()
        elif action == "wipe":
            self.wipe()
        elif action in ("kill", "cancel_shutdown"):
            if not path.isfile(self.config.hosts_path):
                exit(
                    "Hosts file does not exist for cluster: "
                    + self.config.hosts_path
                )
            elif action == "kill":
                print(
                    "Killing all processes started by Muchos "
                    "on {0} cluster".format(self.config.cluster_name)
                )
            elif action == "cancel_shutdown":
                print(
                    "Cancelling automatic shutdown of {0} cluster".format(
                        self.config.cluster_name
                    )
                )
            self.execute_playbook(action + ".yml")
        elif action == "terminate":
            self.terminate()
        else:
            print("ERROR - Unknown action:", action)
