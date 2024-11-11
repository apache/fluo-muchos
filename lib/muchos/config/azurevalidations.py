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

from .base import ConfigValidator
from .azurevalidationhelpers import (
    vmss_status_succeeded_if_exists,
    vmss_cluster_has_appropriate_data_disk_count,
    vmss_exists,
)
from azure.mgmt.compute import ComputeManagementClient
from azure.identity import DefaultAzureCredential


def validate_azure_configs(config, action):
    credential = DefaultAzureCredential()

    # get VM SKU resources for this location. we have to use
    # a specific API version to do this as this resource_skus
    # list operation is not allowed in any other API versions
    # which are available with the version of Azure SDK
    # that ships with Ansible for Azure
    config.client = ComputeManagementClient(
        credential,
        subscription_id=config.azure_subscription_id(),
        api_version="2017-09-01",
    )

    config.vm_skus_for_location = list(
        filter(
            lambda s: s.resource_type == "virtualMachines"
            and config.location() in s.locations,
            config.client.resource_skus.list(),
        )
    )

    # switch to 2018-06-01 API which has support for other operations
    # including VMSS checks
    config.client = ComputeManagementClient(
        credential,
        subscription_id=config.azure_subscription_id(),
        api_version="2018-06-01",
    )

    validations = (
        AZURE_VALIDATIONS["common"] + AZURE_VALIDATIONS[action]
        if action in AZURE_VALIDATIONS
        else []
    )
    return list(
        filter(
            lambda r: isinstance(r, str),
            map(lambda v: v(config, config.client), validations),
        )
    )


AZURE_VALIDATIONS = {
    "common": [
        # if VMSS instances are pending upgrade to latest version
        # block the execution of the setup phase.
        ConfigValidator(
            vmss_status_succeeded_if_exists,
            "VMSS must not exist or be in 'Succeeded' state",
        ),
        # Validate that the data disk configuration is appropriate
        # considering temp disk usage etc.
        ConfigValidator(vmss_cluster_has_appropriate_data_disk_count, None),
        ConfigValidator(lambda config, client: not config.use_multiple_vmss()),
        # the VM SKU specified is not a valid Azure VM SKU
        ConfigValidator(
            lambda config, client: config.vm_sku()
            in {s.name: s for s in config.vm_skus_for_location},
            "azure.vm_sku must be a valid VM SKU for the selected location",
        ),
        ConfigValidator(
            lambda config, client: not config.use_multiple_vmss()
            or all(
                [
                    vmss.get("sku")
                    in {s.name: s for s in config.vm_skus_for_location}
                    for vmss in config.azure_multiple_vmss_vars.get(
                        "vars_list", []
                    )
                ]
            ),
            "when use_multiple_vmss == True, any VMSS with sku "
            "must be a valid VM SKU for the selected location",
        ),
        # Cannot specify Spot (Low Priority) if VMSS SKU is / are not capable
        ConfigValidator(
            lambda config, client: config.getboolean(
                "azure", "use_multiple_vmss"
            )
            or not config.vmss_priority() == "Spot"
            or config.vm_sku() in config.spot_capable_skus(),
            "azure.vm_sku must be an Azure Spot (low priority) capable VM SKU",
        ),
        ConfigValidator(
            lambda config, client: not config.getboolean(
                "azure", "use_multiple_vmss"
            )
            or all(
                [
                    (
                        vmss.get("sku") in config.spot_capable_skus()
                        if vmss.get("vmss_priority") == "Low"
                        else True
                    )
                    for vmss in config.azure_multiple_vmss_vars.get(
                        "vars_list", []
                    )
                ]
            ),
            "when use_multiple_vmss == True, any VMSS set to use Azure Spot "
            "(low priority) must use an Azure Spot-capable VM SKU",
        ),
        # data_disk_sku in
        # ['Standard_LRS', 'StandardSSD_LRS', Premium_LRS']
        ConfigValidator(
            lambda config, client: config.data_disk_sku()
            in ["Standard_LRS", "StandardSSD_LRS", "Premium_LRS"],
            "data_disk_sku must be "
            "one of Standard_LRS, StandardSSD_LRS, or Premium_LRS",
        ),
        ConfigValidator(
            lambda config, client: not config.use_multiple_vmss()
            or all(
                [
                    vmss.get("data_disk_sku")
                    in ["Standard_LRS", "StandardSSD_LRS", "Premium_LRS"]
                    for vmss in config.azure_multiple_vmss_vars.get(
                        "vars_list", []
                    )
                ]
            ),
            "when use_multiple_vmss == True, the data_disk_sku specified for "
            "the VMSS must be one of Standard_LRS, StandardSSD_LRS "
            "or Premium_LRS",
        ),
        # Cannot specify Premium managed disks if VMSS SKU is / are not capable
        ConfigValidator(
            lambda config, client: config.use_multiple_vmss()
            or not config.data_disk_sku() == "Premium_LRS"
            or config.vm_sku() in config.premiumio_capable_skus(),
            "azure.vm_sku must be Premium I/O capable VM SKU "
            "in order to use Premium Managed Disks",
        ),
        ConfigValidator(
            lambda config, client: not config.use_multiple_vmss()
            or all(
                [
                    (
                        vmss.get("sku") in config.premiumio_capable_skus()
                        if vmss.get("data_disk_sku") == "Premium_LRS"
                        else True
                    )
                    for vmss in config.azure_multiple_vmss_vars.get(
                        "vars_list", []
                    )
                ]
            ),
            "when use_multiple_vmss == True, any VMSS set to use Premium "
            "Managed Disks must use a Premium I/O capable VM SKU",
        ),
        # Data disk count specified cannot exceed MaxDataDisks for VM SKU
        ConfigValidator(
            lambda config, client: config.use_multiple_vmss()
            or config.data_disk_count()
            <= config.max_data_disks_for_skus().get(config.vm_sku(), 0),
            "Number of data disks specified exceeds allowed limit for VM SKU",
        ),
        ConfigValidator(
            lambda config, client: not config.use_multiple_vmss()
            or all(
                [
                    vmss.get("data_disk_count")
                    <= config.max_data_disks_for_skus().get(config.vm_sku(), 0)
                    for vmss in config.azure_multiple_vmss_vars.get(
                        "vars_list", []
                    )
                ]
            ),
            "when use_multiple_vmss == True, no VMSS can specify number of "
            "data disks exceeding the allowed limit for the respective VM SKU",
        ),
        # in the multiple VMSS case, a azure_multiple_vmss_vars.yml file
        # must be provided
        ConfigValidator(
            lambda config, client: not config.use_multiple_vmss()
            or hasattr(config, "azure_multiple_vmss_vars"),
            "in the multiple VMSS case, an azure_multiple_vmss_vars.yml"
            " file must be provided",
        ),
        # in the multiple VMSS case, each name suffix should be unique
        ConfigValidator(
            lambda config, client: not config.use_multiple_vmss()
            or len(config.azure_multiple_vmss_vars.get("vars_list", []))
            == len(
                set(
                    [
                        v.get("name_suffix")
                        for v in config.azure_multiple_vmss_vars.get(
                            "vars_list", []
                        )
                    ]
                )
            ),
            "in the multiple VMSS case, each name suffix of a VMSS"
            " must be unique",
        ),
        # ADLS Gen2 is only supported if Accumulo 2.x is used
        ConfigValidator(
            lambda config, client: not config.use_adlsg2()
            or config.version("accumulo").split(".")[0] == "2",
            "ADLS Gen2 support requires Accumulo 2.x",
        ),
    ],
    "launch": [
        # Fail when HDFS HA is NOT enabled and azure_multiple_vmss_vars.yml
        # specifies assignments for HA service roles
        ConfigValidator(
            lambda config, client: not config.use_multiple_vmss()
            or config.hdfs_ha()
            or all(
                (
                    "journalnode" not in current_vmss["roles"]
                    and "zkfc" not in current_vmss["roles"]
                )
                for current_vmss in config.azure_multiple_vmss_vars[
                    "vars_list"
                ]
            ),
            "HDFS HA is NOT enabled, but azure_multiple_vmss_vars.yml "
            "specifies assignments for HA service roles",
        ),
        # Fail when HDFS HA is enabled and azure_multiple_vmss_vars.yml
        # does NOT specify nodes with HA service roles
        ConfigValidator(
            lambda config, client: not config.use_multiple_vmss()
            or not config.hdfs_ha()
            or
            # TODO implement a count based check for the below,
            # do not just check existence of ZKFC and Journal Node roles
            (
                any(
                    ("journalnode" in current_vmss["roles"])
                    for current_vmss in config.azure_multiple_vmss_vars[
                        "vars_list"
                    ]
                )
                and any(
                    ("zkfc" in current_vmss["roles"])
                    for current_vmss in config.azure_multiple_vmss_vars[
                        "vars_list"
                    ]
                )
            ),
            "HDFS HA is enabled, but azure_multiple_vmss_vars.yml does NOT"
            " specify ZKFC and / or Journal Node service roles",
        ),
    ],
    "setup": [
        ConfigValidator(
            vmss_exists,
            "VMSS must exist, please run launch first before running setup",
        ),
    ],
    "wipe": [
        ConfigValidator(vmss_exists, "VMSS must exist to allow running wipe")
    ],
    "terminate": [
        ConfigValidator(
            vmss_exists, "VMSS must exist to allow running terminate"
        )
    ],
}
