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
from azure.common.client_factory import get_client_from_cli_profile
from azure.mgmt.compute import ComputeManagementClient
from .existing import ExistingCluster


# For Muchos deployments on Microsoft Azure, we use Virtual Machine Scale Sets
# VMSS is the most efficient way to provision large numbers of VMs in Azure
class VmssCluster(ExistingCluster):
    def __init__(self, config):
        ExistingCluster.__init__(self, config)

    def launch(self):
        config = self.config
        azure_config = dict(config.items("azure"))
        azure_config["admin_username"] = config.get("general", "cluster_user")
        azure_config["hdfs_ha"] = config.get("general", "hdfs_ha")
        azure_config["vmss_name"] = config.cluster_name
        azure_config["deploy_path"] = config.deploy_path
        azure_config = {
            k: VmssCluster._parse_config_value(v)
            for k, v in azure_config.items()
        }
        subprocess.call(
            [
                "ansible-playbook",
                path.join(config.deploy_path, "ansible/azure.yml"),
                "--extra-vars",
                json.dumps(azure_config),
            ]
        )

    def status(self):
        config = self.config
        azure_vars_dict = dict(config.items("azure"))
        compute_client = get_client_from_cli_profile(ComputeManagementClient)
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
                        config.deploy_path, "ansible/azure_terminate.yml",
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
                path.join(config.deploy_path, "ansible/azure_wipe.yml",),
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
