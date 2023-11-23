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
from yaml import load, FullLoader
from .azurevalidations import validate_azure_configs


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

        # load azure_multiple_vmss_vars.yml
        if self.use_multiple_vmss():
            with open(
                "conf/azure_multiple_vmss_vars.yml"
            ) as azure_multiple_vmss_vars_file:
                self.azure_multiple_vmss_vars = load(
                    azure_multiple_vmss_vars_file.read(), Loader=FullLoader
                )

    def verify_config(self, action):
        self._verify_config(action)

        results = validate_azure_configs(self, action)
        if len(results) > 0:
            exit("ERROR - config failed validation {}".format(results))

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

    def data_dirs_internal(
        self,
        nodeType,
        num_disks=None,
        mount_root_actual=None,
        curr_vm_sku=None,
    ):
        data_dirs = []

        num_disks = self.data_disk_count() if num_disks is None else num_disks
        mount_root_actual = (
            self.mount_root()
            if mount_root_actual is None
            else mount_root_actual
        )
        curr_vm_sku = self.vm_sku() if curr_vm_sku is None else curr_vm_sku

        # Check if using temp storage (non-NVME) for HDFS
        if num_disks == 0 and mount_root_actual == "/mnt/resource":
            data_dirs.append(mount_root_actual)
            return data_dirs

        # Check if using Lsv2 or Lsv3 NVME temp storage for HDFS
        nvme_vm_disk_map = {
            "Standard_L8s_v2": 1,
            "Standard_L16s_v2": 2,
            "Standard_L32s_v2": 4,
            "Standard_L48s_v2": 6,
            "Standard_L64s_v2": 8,
            "Standard_L80s_v2": 10,
            "Standard_L8s_v3": 1,
            "Standard_L16s_v3": 2,
            "Standard_L32s_v3": 4,
            "Standard_L48s_v3": 6,
            "Standard_L64s_v3": 8,
            "Standard_L80s_v3": 10,
            "Standard_L8as_v3": 1,
            "Standard_L16as_v3": 2,
            "Standard_L32as_v3": 4,
            "Standard_L48as_v3": 6,
            "Standard_L64as_v3": 8,
            "Standard_L80as_v3": 10,
        }

        if num_disks == 0 and curr_vm_sku in nvme_vm_disk_map.keys():
            # pretend that we have N data disks
            # in this case those are NVME temp disks
            num_disks = nvme_vm_disk_map[curr_vm_sku]

        # Persistent data disks attached to VMs
        range_var = num_disks + 1
        for diskNum in range(1, range_var):
            data_dirs.append(mount_root_actual + str(diskNum))

        return data_dirs

    def data_dirs_common(self, nodeType):
        return self.data_dirs_internal(nodeType, None, None, None)

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
    @is_valid(is_type(int))
    def os_disk_size_gb(self):
        return self.getint("azure", "os_disk_size_gb", fallback=None)

    @ansible_host_var
    @is_valid(is_type(int))
    def disk_size_gb(self):
        return self.getint("azure", "disk_size_gb")

    @ansible_host_var
    @default("ReadOnly")
    @is_valid(is_in(["ReadOnly", "ReadWrite", "None"]))
    def data_disk_caching(self):
        return self.getint("azure", "data_disk_caching")

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

    @ansible_host_var
    @default("almalinux-x86_64|almalinux|9-gen2|latest||")
    def azure_image_reference(self):
        return self.get("azure", "azure_image_reference")

    @ansible_host_var
    @default("|||")
    def azure_image_plan(self):
        return self.get("azure", "azure_image_plan")

    @ansible_host_var
    @default("")
    def azure_image_cloud_init_file(self):
        return self.get("azure", "azure_image_cloud_init_file", fallback=None)

    @ansible_host_var
    def azure_proxy_image_reference(self):
        apir = self.get("azure", "azure_proxy_image_reference", fallback=None)
        if apir is None or apir == "":
            apir = self.get("azure", "azure_image_reference")
        return apir

    @ansible_host_var
    @default("|||")
    def azure_proxy_image_plan(self):
        apip = self.get("azure", "azure_proxy_image_plan", fallback=None)
        if apip is None or apip == "":
            apip = self.get("azure", "azure_image_plan")
        return apip

    @ansible_host_var
    def azure_proxy_image_cloud_init_file(self):
        apir = self.get(
            "azure", "azure_proxy_image_cloud_init_file", fallback=None
        )
        if apir is None or apir == "":
            apir = self.get(
                "azure", "azure_image_cloud_init_file", fallback=None
            )
        return apir

    @ansible_host_var(name="az_oms_integration_needed")
    @default(False)
    @is_valid(is_in([True, False]))
    def omsIntegrationNeeded(self):
        return self.getboolean("azure", "az_oms_integration_needed")

    @ansible_host_var(name="az_logs_resource_id")
    @default(None)
    def logs_resource_id(self):
        return self.get("azure", "az_logs_resource_id")

    @ansible_host_var(name="az_logs_id")
    @default(None)
    def logs_id(self):
        return self.get("azure", "az_logs_id")

    @ansible_host_var(name="az_logs_key")
    @default(None)
    def logs_key(self):
        return self.get("azure", "az_logs_key")

    @ansible_host_var(name="az_use_app_insights")
    @default(False)
    @is_valid(is_in([True, False]))
    def az_use_app_insights(self):
        return self.getboolean("azure", "az_use_app_insights")

    @ansible_host_var(name="az_appinsights_connection_string")
    @default(None)
    def az_appinsights_connection_string(self):
        return self.get("azure", "az_appinsights_connection_string")

    @ansible_host_var(name="az_app_insights_version")
    @default("3.2.1")
    def az_app_insights_version(self):
        return self.getboolean("azure", "az_app_insights_version")

    @ansible_host_var(name="az_app_insights_home")
    @default("{{ install_dir }}/appinsights-{{ az_app_insights_version }}")
    def az_app_insights_home(self):
        return self.getboolean("azure", "az_app_insights_home")

    @ansible_host_var(name="use_adlsg2")
    @is_valid(is_in([True, False]))
    @default(False)
    def use_adlsg2(self):
        return self.getboolean("azure", "use_adlsg2")

    @ansible_host_var
    @default("Standard_LRS")
    @is_valid(
        is_in(
            [
                "Standard_LRS",
                "Standard_GRS",
                "Standard_RAGRS",
                "Standard_ZRS",
                "Premium_LRS",
            ]
        )
    )
    def adls_storage_type(self):
        return self.get("azure", "adls_storage_type")

    @ansible_host_var
    def user_assigned_identity(self):
        return self.get("azure", "user_assigned_identity")

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

    @ansible_host_var
    @default(None)
    def instance_volumes_input(self):
        return self.get("azure", "instance_volumes_input")

    @ansible_host_var(name="instance_volumes_adls")
    @default(None)
    def instance_volumes_adls(self):
        return self.get("azure", "instance_volumes_adls")

    @ansible_host_var
    @default(False)
    @is_valid(is_in([True, False]))
    def use_multiple_vmss(self):
        return self.getboolean("azure", "use_multiple_vmss")

    @ansible_host_var
    @is_valid(is_type(int))
    def numnodes(self):
        return self.getint("azure", "numnodes")

    @ansible_host_var
    @default(None)
    def azure_subscription_id(self):
        return self.get("azure", "azure_subscription_id")

    @ansible_host_var
    @default(None)
    def resource_group(self):
        return self.get("azure", "resource_group")

    @ansible_host_var
    @default(None)
    def vnet(self):
        return self.get("azure", "vnet")

    @ansible_host_var
    @default(None)
    def vnet_cidr(self):
        return self.get("azure", "vnet_cidr")

    @ansible_host_var
    @default(None)
    def subnet(self):
        return self.get("azure", "subnet")

    @ansible_host_var
    @default(None)
    def subnet_cidr(self):
        return self.get("azure", "subnet_cidr")

    @ansible_host_var
    @default(None)
    def location(self):
        return self.get("azure", "location")

    @ansible_host_var
    @default("")
    def azure_proxy_host(self):
        return self.get("azure", "azure_proxy_host")

    @ansible_host_var
    @default("Standard_D8s_v3")
    def azure_proxy_host_vm_sku(self):
        return self.get("azure", "azure_proxy_host_vm_sku")

    @ansible_host_var
    @is_valid(is_in(["None", "Spot"]))
    def vmss_priority(self):
        return self.get("azure", "vmss_priority")

    @ansible_host_var
    @default("Standard_LRS")
    @is_valid(is_in(["Standard_LRS", "Premium_LRS", "StandardSSD_LRS"]))
    def data_disk_sku(self):
        return self.get("azure", "data_disk_sku")

    @ansible_host_var
    def accnet_capable_skus(self):
        return list(
            map(
                lambda r: r.name,
                filter(
                    lambda s: len(
                        list(
                            filter(
                                lambda c: c.name
                                == "AcceleratedNetworkingEnabled"
                                and c.value == "True",
                                s.capabilities,
                            )
                        )
                    )
                    > 0,
                    self.vm_skus_for_location,
                ),
            )
        )

    @ansible_host_var
    def premiumio_capable_skus(self):
        return list(
            map(
                lambda r: r.name,
                filter(
                    lambda s: len(
                        list(
                            filter(
                                lambda c: c.name == "PremiumIO"
                                and c.value == "True",
                                s.capabilities,
                            )
                        )
                    )
                    > 0,
                    self.vm_skus_for_location,
                ),
            )
        )

    def spot_capable_skus(self):
        return list(
            map(
                lambda r: r.name,
                filter(
                    lambda s: len(
                        list(
                            filter(
                                lambda c: c.name == "LowPriorityCapable"
                                and c.value == "True",
                                s.capabilities,
                            )
                        )
                    )
                    > 0,
                    self.vm_skus_for_location,
                ),
            )
        )

    def max_data_disks_for_skus(self):
        n = list(map(lambda r: r.name, self.vm_skus_for_location))
        d = list(
            map(
                lambda s: int(
                    next(
                        filter(
                            lambda c: c.name == "MaxDataDiskCount",
                            s.capabilities,
                        )
                    ).value
                ),
                self.vm_skus_for_location,
            )
        )
        return dict(zip(n, d))
