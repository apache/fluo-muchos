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


def vmss_status_succeeded_if_exists(config, client):
    multi_vmss = config.getboolean("azure", "use_multiple_vmss")
    resource_group = config.get("azure", "resource_group")
    if not multi_vmss:
        try:
            vmss = client.virtual_machine_scale_sets.get(
                resource_group_name=resource_group,
                vm_scale_set_name=config.cluster_name,
            )
        except:  # noqa
            return True
        else:
            return vmss.provisioning_state == "Succeeded"
    else:
        for vmss_config in config.azure_multiple_vmss_vars.get(
            "vars_list", []
        ):
            cluster_name = "{}-{}".format(
                config.cluster_name, vmss_config.get("name_suffix", "")
            )
            try:
                vmss = client.virtual_machine_scale_sets.get(
                    resource_group_name=resource_group,
                    vm_scale_set_name=cluster_name,
                )
            except:  # noqa
                pass
            else:
                if vmss.provisioning_state != "Succeeded":
                    return False
        return True


def validate_disk_count(
    context,
    specified_disk_count,
    mount_root,
    disk_pattern,
    validation_errors,
):
    # min_data_disk_count is 1 unless we are using exclusively
    # ephemeral storage (data_disk_count is 0), which in turn is when:
    # mount_root is /mnt/resource OR
    # azure_disk_device_pattern is nvme*n1
    min_data_disk_count = 1
    using_temporary_disks = False

    if mount_root == "/mnt/resource" or disk_pattern == "nvme*n1":
        min_data_disk_count = 0
        using_temporary_disks = True

    # also ensure that the mount root is not /mnt/resource
    # when the NVME drives are being used
    if mount_root == "/mnt/resource" and disk_pattern == "nvme*n1":
        validation_errors.append(
            "mount_root cannot be "
            "/mnt/resource when using  NVME temp disks!"
        )

    # additional check to ensure that we don't have data disks specified
    # when using temp storage
    if using_temporary_disks and specified_disk_count > 0:
        validation_errors.append(
            "Config error for {}: data_disk_count must be 0 "
            "when using temporary storage!".format(context)
        )

    # final check if using persistent storage (implied through the variable
    # min_data_disk_count) that there are sufficient data disks configured
    if specified_disk_count < min_data_disk_count:
        validation_errors.append(
            "Config error for {}: data_disk_count "
            "must be >= {}!".format(context, min_data_disk_count)
        )

    return


def vmss_cluster_has_appropriate_data_disk_count(config, client):
    multi_vmss = config.use_multiple_vmss()
    disk_validation_errors = []

    if not multi_vmss:
        validate_disk_count(
            "Cluster",
            config.data_disk_count(),
            config.mount_root(),
            config.azure_disk_device_pattern(),
            disk_validation_errors,
        )
    else:
        for vmss in config.azure_multiple_vmss_vars.get("vars_list", []):
            validate_disk_count(
                "VMSS {}".format(vmss.get("name_suffix")),
                vmss.get("data_disk_count", 0),
                vmss.get("mount_root", config.mount_root()),
                vmss.get(
                    "azure_disk_device_pattern",
                    config.azure_disk_device_pattern(),
                ),
                disk_validation_errors,
            )

    if len(disk_validation_errors) > 0:
        return " ".join(disk_validation_errors)


def vmss_exists(config, client):
    multi_vmss = config.getboolean("azure", "use_multiple_vmss")
    resource_group = config.get("azure", "resource_group")
    if not multi_vmss:
        try:
            _ = client.virtual_machine_scale_sets.get(
                resource_group_name=resource_group,
                vm_scale_set_name=config.cluster_name,
            )
        except:  # noqa
            return False
        else:
            return True
    else:
        for vmss_config in config.azure_multiple_vmss_vars.get(
            "vars_list", []
        ):
            cluster_name = "{}-{}".format(
                config.cluster_name, vmss_config.get("name_suffix", "")
            )
            try:
                _ = client.virtual_machine_scale_sets.get(
                    resource_group_name=resource_group,
                    vm_scale_set_name=cluster_name,
                )
            except:  # noqa
                return False
        return True
