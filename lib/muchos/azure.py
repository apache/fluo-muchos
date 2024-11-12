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

import json
import subprocess
from os import path
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from .existing import ExistingCluster


# For Muchos deployments on Microsoft Azure, we use Virtual Machine Scale Sets
# VMSS is the most efficient way to provision large numbers of VMs in Azure
class VmssCluster(ExistingCluster):
    def __init__(self, config):
        ExistingCluster.__init__(self, config)

    def launch(self):
        config = self.config
        azure_config = config.ansible_host_vars()
        azure_config["vmss_name"] = config.cluster_name

        retcode = subprocess.call(
            [
                "ansible-playbook",
                path.join(config.deploy_path, "ansible/azure.yml"),
                "--extra-vars",
                json.dumps(azure_config),
            ]
        )
        if retcode != 0:
            exit(
                "ERROR - Command failed with return code of {0}".format(
                    retcode
                )
            )

    def status(self):
        config = self.config
        azure_vars_dict = dict(config.items("azure"))
        credential = DefaultAzureCredential()
        compute_client = ComputeManagementClient(
            credential, azure_vars_dict["azure_subscription_id"]
        )
        vmss_status = compute_client.virtual_machine_scale_sets.get(
            azure_vars_dict["resource_group"], self.config.cluster_name
        )
        print(
            "name:",
            vmss_status.name,
            "\nprovisioning_state:",
            vmss_status.provisioning_state,
        )

    def terminate(self):
        config = self.config
        azure_config = dict(config.items("azure"))
        azure_config["vmss_name"] = config.cluster_name
        azure_config["deploy_path"] = config.deploy_path
        azure_config = {
            k: VmssCluster._parse_config_value(v)
            for k, v in azure_config.items()
        }
        print(
            "All of the Muchos resources provisioned in resource group '{0}'"
            " will be deleted!".format(azure_config["resource_group"])
        )

        response = input("Do you want to continue? (y/n) ")
        if response == "y":
            subprocess.call(
                [
                    "ansible-playbook",
                    path.join(
                        config.deploy_path,
                        "ansible/azure_terminate.yml",
                    ),
                    "--extra-vars",
                    json.dumps(azure_config),
                ]
            )
        else:
            print("Aborted termination")

    def wipe(self):
        super().wipe()
        # Wipe ADLS Gen2 storage accounts if implemented
        config = self.config
        azure_config = dict(config.items("azure"))
        azure_config["vmss_name"] = config.cluster_name
        azure_config["cluster_type"] = config.get("general", "cluster_type")
        azure_config["deploy_path"] = config.deploy_path
        azure_config = {
            k: VmssCluster._parse_config_value(v)
            for k, v in azure_config.items()
        }
        retcode = subprocess.call(
            [
                "ansible-playbook",
                path.join(
                    config.deploy_path,
                    "ansible/azure_wipe.yml",
                ),
                "--extra-vars",
                json.dumps(azure_config),
            ]
        )
        if retcode != 0:
            exit(
                "ERROR - Command failed with return code of {0}".format(
                    retcode
                )
            )

    def _parse_config_value(v):  # noqa
        if v.isdigit():
            return int(v)
        if v.lower() in ("true", "yes"):
            return True
        if v.lower() in ("false", "no"):
            return False
        return v

    # For Azure clusters this method creates Ansible group variables which
    # allow overriding the "global" host or play variables with group specific
    # variables. Because Ansible group variables override host variables this
    # is a very powerful feature to support per-group specialization of
    # configuration. Currently this is used to define the following:
    #
    # 1. Variables for different perf profiles for different groups of hosts
    #    This capability allows specifying different settings for clusters
    #    which have heterogenous hardware - RAM especially
    #
    # 2. Different mount roots for different sets of hosts, with a fallback to
    #    using the global mount_root defined in the Ansible hosts file
    #
    # 3. Different worker_data_dirs and default_data_dirs for specific groups
    #    of hosts.
    #
    # 4. Different Azure disk path and disk name pattern for specific groups
    #    of hosts.
    def add_specialized_configs(self, hosts_file):
        if self.config.use_multiple_vmss():
            vmss_hosts = open(
                path.join(
                    self.config.deploy_path, "conf/azure_vmss_to_hosts.conf"
                ),
                "r",
            )
            print("\n", file=hosts_file)
            for line in vmss_hosts:
                print(line.rstrip("\n"), file=hosts_file)

            for curr_vmss in self.config.azure_multiple_vmss_vars["vars_list"]:
                vmss_group_name = (
                    self.config.cluster_name + "-" + curr_vmss["name_suffix"]
                )
                profile = curr_vmss["perf_profile"]

                with open(
                    path.join(
                        self.config.deploy_path,
                        "ansible/group_vars/"
                        + vmss_group_name.replace("-", "_"),
                    ),
                    "w",
                ) as vmss_file:
                    for name, value in self.config.items(profile):
                        print("{0}: {1}".format(name, value), file=vmss_file)

                    # use VMSS-specific mount root if one is defined or
                    # the global mount root if there is no VMSS-specific value
                    curr_mount_root = curr_vmss.get(
                        "mount_root", self.config.mount_root()
                    )

                    # write the mount root out to the per-VMSS group vars
                    print(
                        "{0}: {1}".format("mount_root", curr_mount_root),
                        file=vmss_file,
                    )

                    # also include per-VMSS worker_data_dirs
                    curr_worker_dirs = self.config.data_dirs_internal(
                        "worker",
                        curr_vmss["data_disk_count"],
                        curr_mount_root,
                        curr_vmss["sku"],
                    )

                    print(
                        "{0}: {1}".format(
                            "worker_data_dirs",
                            curr_worker_dirs,
                        ),
                        file=vmss_file,
                    )

                    # per-VMSS default_data_dirs
                    curr_default_dirs = self.config.data_dirs_internal(
                        "default",
                        curr_vmss["data_disk_count"],
                        curr_mount_root,
                        curr_vmss["sku"],
                    )

                    print(
                        "{0}: {1}".format(
                            "default_data_dirs",
                            curr_default_dirs,
                        ),
                        file=vmss_file,
                    )

                    # also write out per-VMSS disk path and pattern
                    # using the global value from muchos.props as default
                    # if the VMSS does not define a custom value
                    print(
                        "{0}: {1}".format(
                            "azure_disk_device_path",
                            curr_vmss.get(
                                "azure_disk_device_path",
                                self.config.azure_disk_device_path(),
                            ),
                        ),
                        file=vmss_file,
                    )

                    print(
                        "{0}: {1}".format(
                            "azure_disk_device_pattern",
                            curr_vmss.get(
                                "azure_disk_device_pattern",
                                self.config.azure_disk_device_pattern(),
                            ),
                        ),
                        file=vmss_file,
                    )

                    # these nested loops are a tight (if slightly less
                    # readable way) of creating the various directory ordinals
                    for dirtype in ["default", "worker"]:
                        for ordinal in range(3):
                            print(
                                "{0}: {1}".format(
                                    "{0}dir_ordinal{1}".format(
                                        dirtype, ordinal
                                    ),
                                    (
                                        0
                                        if len(
                                            curr_default_dirs
                                            if dirtype == "default"
                                            else curr_worker_dirs
                                        )
                                        < ordinal + 1
                                        else ordinal
                                    ),
                                ),
                                file=vmss_file,
                            )
