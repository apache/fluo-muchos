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


def validate_azure_configs(config, action):
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
        ConfigValidator(
            lambda config, client: not config.getboolean(
                "azure", "use_multiple_vmss"
            )
        ),
        # the VM SKU specified is not a valid Azure VM SKU
        ConfigValidator(
            lambda config, client: config.get("azure", "vm_sku")
            in {s.name: s for s in config.vm_skus_for_location},
            "azure.vm_sku must be a valid VM SKU for the selected location",
        ),
        ConfigValidator(
            lambda config, client: not config.getboolean(
                "azure", "use_multiple_vmss"
            )
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
        # managed_disk_type in
        # ['Standard_LRS', 'StandardSSD_LRS', Premium_LRS']
        ConfigValidator(
            lambda config, client: config.get("azure", "managed_disk_type")
            in ["Standard_LRS", "StandardSSD_LRS", "Premium_LRS"],
            "managed_disk_type must be "
            "one of Standard_LRS, StandardSSD_LRS, or Premium_LRS",
        ),
        ConfigValidator(
            lambda config, client: not config.getboolean(
                "azure", "use_multiple_vmss"
            )
            or all(
                [
                    vmss.get("disk_sku") in
                    ["Standard_LRS",  "StandardSSD_LRS", "Premium_LRS"]
                    for vmss in config.azure_multiple_vmss_vars.get(
                        "vars_list", []
                    )
                ]
            ),
            "when use_multiple_vmss == True, any VMSS with disk_sku must "
            "be one of Standard_LRS, StandardSSD_LRS or Premium_LRS",
        ),
        # Cannot specify Premium managed disks if VMSS SKU is / are not capable
        ConfigValidator(
            lambda config, client: config.getboolean(
                "azure", "use_multiple_vmss"
            )
            or not config.managed_disk_type() == "Premium_LRS"
            or config.vm_sku() in config.premiumio_capable_skus(),
            "azure.vm_sku must be Premium I/O capable VM SKU "
            "in order to use Premium Managed Disks",
        ),
        ConfigValidator(
            lambda config, client: not config.getboolean(
                "azure", "use_multiple_vmss"
            )
            or all(
                [
                    vmss.get("sku") in config.premiumio_capable_skus()
                    if vmss.get("disk_sku") == "Premium_LRS"
                    else True
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
            lambda config, client: config.getboolean(
                "azure", "use_multiple_vmss"
            )
            or config.data_disk_count()
            <= config.max_data_disks_for_skus()[config.vm_sku()],
            "Number of data disks specified exceeds allowed limit for VM SKU",
        ),
        ConfigValidator(
            lambda config, client: not config.getboolean(
                "azure", "use_multiple_vmss"
            )
            or all(
                [
                    vmss.get("data_disk_count")
                    <= config.max_data_disks_for_skus()[vmss.get("sku")]
                    for vmss in config.azure_multiple_vmss_vars.get(
                        "vars_list", []
                    )
                ]
            ),
            "when use_multiple_vmss == True, no VMSS can specify number of "
            "data disks exceeding the allowed limit for the respective VM SKU",
        ),
        # in the multiple VMSS case, a azure_multiple_vmss_vars.yml
        # should exist
        ConfigValidator(
            lambda config, client: not config.getboolean(
                "azure", "use_multiple_vmss"
            )
            or hasattr(config, "azure_multiple_vmss_vars"),
            "when use_multiple_vmss == True, "
            "conf/azure_multiple_vmss_vars.yml to exist",
        ),
        # in the multiple VMSS case, each name suffix should be unique
        ConfigValidator(
            lambda config, client: not config.getboolean(
                "azure", "use_multiple_vmss"
            )
            or len(config.azure_multiple_vmss_vars.get(
                "vars_list", []
            ))
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
            "when use_multiple_vmss == True, "
            "each name_suffix of a vmss must be unique",
        ),
        # ADLS Gen2 is only supported if Accumulo 2.x is used
        ConfigValidator(
            lambda config, client: not config.use_adlsg2()
            or config.version("accumulo").split(".")[0] == "2",
            "ADLS Gen2 support requires Accumulo 2.x",
        ),
    ],
    "launch": [],
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
