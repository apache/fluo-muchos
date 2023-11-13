# Azure VM images
Muchos can be configured to use any Azure Marketplace image, including those that need a payment plan. In addition, Muchos can be configured to use a custom VM image which has been uploaded to an Azure subscription, or a VM image which exists in a shared image gallery.

# Cluster image configuration
The sections below describe the various image related configurations in `muchos.props`.

## azure_image_reference
`azure_image_reference` is a pipe-delimited string in the format `offer|publisher|sku|version|image_id|`. The trailing pipe character is intentional.

* For Azure Marketplace images, the values for the fields `offer|publisher|sku|version` can be obtained from the Azure portal, or by using the Azure CLI commands as shown later. For example, the CentOS 7.9 image currently used as the default in Muchos is specified as:

    `CentOS|OpenLogic|7_9|latest||`

  In the above case, since it's a marketplace image, the last value of `image_id` is empty.

* It is also possible to use a [custom Azure image](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/imaging) with Muchos. For using an image from an Azure Compute Gallery ("Shared Image Gallery"), the full resource ID of the image should be specified for `image_id` and the other fields should not be specified. For example:

    `||||//subscriptions/AZURE_SUBSCRIPTION_ID/resourceGroups/RESOURCE_GROUP/providers/Microsoft.Compute/galleries/SHARED_GALLERY_NAME/images/SHARED_IMAGE_NAME/versions/SHARED_IMAGE_VERSION|`

  For more information on creating an image in an Azure compute gallery, see [Tutorial: Create a custom image of an Azure VM with the Azure CLI](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/tutorial-custom-images). Some Linux distributions like Fedora make available [a VHD file specifically for Azure](https://fedoraproject.org/cloud/download) which can then be [converted to a fixed-size disk](https://learn.microsoft.com/en-us/azure/virtual-machines/windows/prepare-for-upload-vhd-image#convert-the-virtual-disk-to-a-fixed-size-vhd) and uploaded to Azure for creating a custom image. In the case of the Fedora image, the `Fedora-Cloud-Base-Azure-39-1.5.x86_64.vhd` needs to be resized to a fixed-size VHD of size 6,442,450,944 bytes before uploading to Azure.

* For legacy managed images (not from a gallery), the full resource ID of the image should be specified in place of `image_id`, and the other fields should not be specified. For example:

    `||||/subscriptions/AZURE_SUBSCRIPTION_ID/resourceGroups/RESOURCE_GROUP/providers/Microsoft.Compute/images/CUSTOM_IMAGE_NAME|`

  For more information on legacy managed images see [Create a legacy managed image of a generalized VM in Azure](https://learn.microsoft.com/en-us/azure/virtual-machines/capture-image-resource).

## azure_image_plan
`azure_image_plan` is only needed when working with images which require payment plan information to be supplied when a VM or VMSS is being created using that image. The format of this configuration is `plan_name|product|publisher|`. Plan information for the images published by a given publisher can easily be queried by using the Azure CLI. For example, to query the plan information for a Rocky Linux image in Azure:

    `az vm image show --urn "erockyenterprisesoftwarefoundationinc1653071250513:rockylinux:free:latest" --query "plan"`

Then using that information, `azure_image_plan` can be configured as below in muchos.props:

    `azure_image_plan = free|rockylinux|erockyenterprisesoftwarefoundationinc1653071250513|`

## azure_image_cloud_init_file
`azure_image_cloud_init_file` is used to optionally specify the name of a cloud-init file to be used. Only specify the filename here, and make sure that the file exists under the `ansible/roles/azure/files` directory in this repo.

# Proxy image configuration
If needed, there are optional configurations to allow using a different image for the optional proxy. The following configurations follow exactly the same formats as their cluster image counterparts.
* `azure_proxy_image_reference`
* `azure_proxy_image_plan`
* `azure_proxy_image_cloud_init_file`

By default, these configurations are commented out in the muchos.props file, and the corresponding values from the cluster image configurations are used.

# Other useful commands
You can run the below Azure CLI command to determine the list of SKU's available for a given product and publisher in a given region:

```bash
az vm image list-skus -l <region> -f AlmaLinux -p AlmaLinux -o table
```
For illustration, provided a sample output that displays the sku list from `westus2` region. The sku name `8-gen1, 8-gen2` refer to [Azure VMs generations](https://learn.microsoft.com/en-us/azure/virtual-machines/generation-2). 

```bash
$ az vm image list-skus -l westus2 -f AlmaLinux -p AlmaLinux -o table
Location    Name
----------  --------
westus2     8-gen1
westus2     8-gen2
westus2     8_4
westus2     8_4-gen2
westus2     8_5
westus2     8_5-gen2
westus2     9-gen1
westus2     9-gen2
```
