# Azure based clusters using multiple Virtual Machine Scale Sets (VMSS)
By default, Azure based deployments of Accumulo clusters provision a single [Virtual Machine Scale Set - VMSS](https://docs.microsoft.com/en-us/azure/virtual-machine-scale-sets/overview). A VMSS consists of a set of Virtual Machine instances, which are individually identified by their hostname and private IP address.

## Challenges with a single VMSS deployment
1. All VM instances in a single VMSS by default are of the same size (CPU, RAM and disks). This can be a constraint when provisioning larger clusters, wherein the user might require different resource sizes for leader nodes as compared to worker nodes.
1. It may also be required to use different disk types (SSD / HDD / NVME) for different sets of nodes in the same Muchos cluster. This is not possible when using a single VMSS deployment.
1. The `muchos launch` command automatically populates the `nodes` section in `muchos.props` with these hostnames and IP addresses based on the details of the VM instances in the VMSS. In the case of a single VMSS deployment, hard-coded assignment of a minimum (but sufficient) set of roles, to these nodes is done. As a result, deploying additional roles, such as Fluo, or Spark, is not possible unless the user manually edits the `muchos.props` file after the `muchos launch` command, and prior to running `muchos setup`.
1. Also, in certain cases, it may be necessary to spawn multiple VMSS deployments, to overcome [limits](https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/azure-subscription-service-limits#virtual-machine-scale-sets-limits) such as the maximum number of VMs in a single VMSS. For example, attempting to launch a 2000-node Azure cluster through Muchos would not work if deploying using a single VMSS, as the current limit for VMSS is 1000 VMs in a single VMSS.
1. Finally, it may be required to assign different perf profiles to different sets of VMs in the cluster. For example, larger nodes will typically have larger JVM heap sizes / YARN memory configured as compared to smaller nodes.

## Multiple VMSS deployment
To address the above challenges, Muchos supports a "multiple VMSS" mode of installation for Azure clusters. To use this mode, the user needs to:
1. Set `use_multiple_vmss = True` in `muchos.props`
1. Create an appropriate `azure_multiple_vmss_vars.yml` file in the `fluo-muchos/conf` folder

In such a case, the `muchos launch` command will create multiple VMSS deployments in parallel, and later assign roles to the VM instances within each VMSS, based on the specification in the `azure_multiple_vmss_vars.yml` file. Subsequently, `muchos setup` runs without any modifications.

## Format of the mutliple_vmss_vars.yml file
Muchos provides a [sample file](../conf/azure_multiple_vmss_vars.yml.example) which can be used as a template to customize. The YAML file is a list of VMSS specifications. The following fields can be specified for each VMSS:

| Attribute | Required or optional? | Default value | Description |
|-----------|------------------------|---------|-------------|
| `name_suffix` | Required | - | The name of each VMSS is constructed by concatenating the Muchos cluster name with this string. As an example, if your Muchos cluster is called `test`, and this field has a value of `ldr`, then the VMSS is created with a name `test-ldr`|
| `sku` | Required | - | A string identifier specifying the Azure VM size. Refer to the [Azure documentation](https://docs.microsoft.com/en-us/azure/virtual-machines/dv3-dsv3-series) to lookup these strings. An example VM size is `Standard_D32s_v3` for a 32-vCPU [Dsv3](https://docs.microsoft.com/en-us/azure/virtual-machines/dv3-dsv3-series#dsv3-series) VM|
| `azure_image_reference` | Optional | - | If, for whatever reason, you need to use a different Azure VM image for a specific VMSS, please specify the image details in the same format as documented in [Azure image reference](./azure-image-reference.md) |
| `azure_image_plan` | Optional | - | If, for whatever reason, you need to use a different Azure VM image for a specific VMSS, and if that image needs purchase plan information to be specified, please specify the plan information the same format as documented in [Azure image reference](./azure-image-reference.md) |
| `azure_image_cloud_init_file` | Optional | - | If, for whatever reason, you need to use a different Azure VM image for a specific VMSS, and if that image needs a custom cloud init file, please specify the cloud init file name as documented in [Azure image reference](./azure-image-reference.md) |
| `vmss_priority` | Optional | None | If this not specified at each VM level, the value for `vmss_priority` from the `azure` section in [muchos.props](../conf/muchos.props.example) is used | This can be set to `None`, for regular VMs, or `Spot` for [Spot VMs](https://docs.microsoft.com/en-us/azure/virtual-machines/windows/spot-vms).|
| `perf_profile` | Required | - | A string identifying a corresponding performance profile configuration section in muchos.props which contains perf profile parameters |
| `azure_disk_device_path`| Optional | If not specified, the corresponding `azure_disk_device_path` value from the `azure` section in [muchos.props](../conf/muchos.props.example) is used | This is a device path used to enumerate attached SCSI or NVME disks to use for persistent local storage |
| `azure_disk_device_pattern`| Optional | If not specified, the corresponding `azure_disk_device_pattern` value from the `azure` section in [muchos.props](../conf/muchos.props.example) is used | This is a device name wildcard pattern used (internally) in conjunction with `azure_disk_device_path` to enumerate attached SCSI or NVME disks to use for persistent local storage |
| `mount_root`| Optional | If not specified, the corresponding `mount_root` value from the `azure` section in [muchos.props](../conf/muchos.props.example) is used | This is the folder in the file system where the persistent disks are mounted |
| `data_disk_count`| Required | - | An integer value which specifies the number of persistent (managed) data disks to be attached to each VM in the VMSS. It can be 0 in specific cases - see [notes on using ephemeral storage](./azure-ephemeral-disks.md) for details |
| `data_disk_sku`| Required | - | Can be either Standard_LRS (for HDD) or Premium_LRS (for Premium SSD). At this time, we have not tested the use of Standard SSD or UltraSSD with Muchos |
| `data_disk_size_gb`| Required | - | An integer value specifying the size of each persistent (managed) data disk in GiB |
| `data_disk_caching`| Optional | ReadOnly | One of None, ReadOnly, or ReadWrite indicating the type of host caching to use for each persistent (managed) disk |
| `image_reference`| Optional | If not specified, the corresponding `azure_image_reference` value from the `azure` section in [muchos.props](../conf/muchos.props.example) is used | Azure image reference defined as a pipe-delimited string.
| `capacity`| Required | - | An integer value specifying the number of VMs in this specific VMSS |
| `roles`| Required | - | This is a dictionary (list of key-value pairs), each of which should be of the form `muchos_role_name`: `integer count`. See [sample file](../conf/azure_multiple_vmss_vars.yml.example) for examples. the `muchos launch` command for Azure clusters uses this list to assign roles to hosts in a sequential fashion. For example, if a given VMSS has 3 `zkfc` role members and 2 `namenode` role members defined, host0 and host1 in the VMSS will be assigned both `zkfc` and `namenode` roles, and host2 in the VMSS will just be assigned a `zkfc` role |
