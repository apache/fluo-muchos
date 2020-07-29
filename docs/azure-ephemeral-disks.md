Using ephemeral storage within clusters deployed by Muchos for Azure
--------------------------------------------------------------------

By default for Azure based clusters, Muchos will create 3 data disks, each of size 128GiB, attached to each VM. These
[managed disks](https://docs.microsoft.com/en-us/azure/virtual-machines/linux/managed-disks-overview) provide
persistent storage which ensures that the data in HDFS is safe and consistent even if the VMs are deallocated (stopped).

However, if you'd like to use only the ephemeral / temporary disk storage for HDFS, you first need to understand that
using temp storage will result in lost data across VM deallocate - start cycles. If that behavior is acceptable
for your dev/test scenario, there are two options available to use ephemeral storage within Azure:
* Use the temporary SSD disk which is available on most VM types. This tends to be smaller in size. Refer to the
[Azure VM sizes](https://docs.microsoft.com/en-us/azure/virtual-machines/dv3-dsv3-series) page for details on temp storage sizes
* Use the [Lsv2 series VMs](https://docs.microsoft.com/en-us/azure/virtual-machines/lsv2-series) which offer larger amounts of NVME based temp storage

For using "regular" temporary storage (non-NVME), you need to change the following within the `azure` section within muchos.props:
* `data_disk_count` needs to be set to 0
* `mount_root` within the `azure` section needs to be set to `/mnt/resource'

If you'd like larger NVME temporary disks, another option is to use the storage-optimized Lsv2 VM type in Azure. To use the
NVME disks available in these VMs, you must change the following within the `azure` section within muchos.props:
* `vm_sku` needs to be set to one of the sizes from [this page](https://docs.microsoft.com/en-us/azure/virtual-machines/lsv2-series), for example Standard_L8s_v2
* `data_disk_count` needs to be set to 0
* `mount_root` within the `azure` section should be set to `/var/data` (which is also the default)
* `azure_disk_device_path` should be set to `/dev`
* `azure_disk_device_pattern` should be set to `nvme*n1`
