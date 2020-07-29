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

from sys import exit
from .base import BaseConfig
from .decorators import ansible_host_var, is_valid, default
from .validators import is_type, is_in


class AzureDeployConfig(BaseConfig):
    def __init__(
        self,
        deploy_path,
        config_path,
        hosts_path,
        checksums_path,
        templates_path,
        cluster_name,
    ):
        super(AzureDeployConfig, self).__init__(
            deploy_path,
            config_path,
            hosts_path,
            checksums_path,
            templates_path,
            cluster_name,
        )

    def verify_config(self, action):
        self._verify_config(action)

        proxy = self.get("general", "proxy_hostname")
        cluster_type = self.get("general", "cluster_type")
        if cluster_type not in ["azure"]:
            if not proxy:
                exit("ERROR - proxy.hostname must be set in muchos.props")

            if proxy not in self.node_d:
                exit(
                    "ERROR - The proxy (set by property proxy_hostname={0}) "
                    "cannot be found in 'nodes' section of "
                    "muchos.props".format(proxy)
                )

    def verify_launch(self):
        pass

    def node_type_map(self):
        return {}

    def mount_root(self):
        return self.get("azure", "mount_root")

    def data_dirs_common(self, nodeType):
        data_dirs = []

        num_disks = self.data_disk_count()

        # Check if using temp storage (non-NVME) for HDFS
        if num_disks == 0 and self.mount_root() == "/mnt/resource":
            data_dirs.append(self.mount_root())
            return data_dirs

        # Check if using Lsv2 NVME temp storage for HDFS
        lsv2_vm_disk_map = {
            "Standard_L8s_v2": 1,
            "Standard_L16s_v2": 2,
            "Standard_L32s_v2": 4,
            "Standard_L48s_v2": 6,
            "Standard_L64s_v2": 8,
            "Standard_L80s_v2": 10,
        }

        if num_disks == 0 and self.vm_sku() in lsv2_vm_disk_map.keys():
            # pretend that we have N data disks
            # in this case those are NVME temp disks
            num_disks = lsv2_vm_disk_map[self.vm_sku()]

        # Persistent data disks attached to VMs
        range_var = num_disks + 1
        for diskNum in range(1, range_var):
            data_dirs.append(self.mount_root() + str(diskNum))

        return data_dirs

    def metrics_drive_ids(self):
        drive_ids = []
        range_var = self.data_disk_count() + 1
        for i in range(1, range_var):
            drive_ids.append(self.get("azure", "metrics_drive_root") + str(i))
        return drive_ids

    @ansible_host_var
    def vm_sku(self):
        return self.get("azure", "vm_sku")

    @ansible_host_var
    @is_valid(is_type(int))
    def data_disk_count(self):
        return self.getint("azure", "data_disk_count")

    @ansible_host_var
    @default("/dev/disk/azure/scsi1")
    def azure_disk_device_path(self):
        return self.get("azure", "azure_disk_device_path")

    @ansible_host_var
    @default("lun*")
    def azure_disk_device_pattern(self):
        return self.get("azure", "azure_disk_device_pattern")

    @ansible_host_var
    @default(None)
    def azure_fileshare_mount(self):
        return self.get("azure", "azure_fileshare_mount")

    @ansible_host_var
    @default(None)
    def azure_fileshare(self):
        return self.get("azure", "azure_fileshare")

    @ansible_host_var
    @default(None)
    def azure_fileshare_username(self):
        return self.get("azure", "azure_fileshare_username")

    @ansible_host_var
    @default(None)
    def azure_fileshare_password(self):
        return self.get("azure", "azure_fileshare_password")

    @ansible_host_var(name="az_oms_integration_needed")
    @default(False)
    @is_valid(is_in([True, False]))
    def omsIntegrationNeeded(self):
        return self.getboolean("azure", "az_oms_integration_needed")

    @ansible_host_var(name="az_logs_id")
    @default(None)
    def logs_id(self):
        return self.get("azure", "az_logs_id")

    @ansible_host_var(name="az_logs_key")
    @default(None)
    def logs_key(self):
        return self.get("azure", "az_logs_key")

    @ansible_host_var(name="use_adlsg2")
    @is_valid(is_in([True, False]))
    @default(False)
    def use_adlsg2(self):
        return self.getboolean("azure", "use_adlsg2")

    @ansible_host_var(name="azure_tenant_id")
    @default(None)
    def azure_tenant_id(self):
        return self.get("azure", "azure_tenant_id")

    @ansible_host_var(name="azure_client_id")
    @default(None)
    def azure_client_id(self):
        return self.get("azure", "azure_client_id")

    @ansible_host_var(name="principal_id")
    @default(None)
    def principal_id(self):
        return self.get("azure", "principal_id")

    @ansible_host_var(name="instance_volumes_adls")
    @default(None)
    def instance_volumes_adls(self):
        return self.get("azure", "instance_volumes_adls")
