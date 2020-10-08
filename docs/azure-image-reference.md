Configure Azure image with CentOS 8.x
--------------------------------------

To configure CentOS 8.x, simply modify the `sku` as shown below. This will install CentOS 8.2 Generation 2 Azure VMs. To know more about Generation 2 VMs on Azure, please visit the [doc](https://docs.microsoft.com/en-us/azure/virtual-machines/generation-2)
```bash
CentOS|OpenLogic|8_2-gen2|latest|
```
Run the Azure CLI command to determine the list of SKU's available for CentOS in a given region
```bash
az vm image list-skus -l <region> -f CentOS -p OpenLogic -o table
```
For illustration, provided a sample output that displays the sku list from `westus2` region. The sku name `8_1, 8_2` implicitly refers to Generation 1 Azure VMs.
```bash
$ az vm image list-skus -l westus2 -f CentOS -p OpenLogic -o table
Location    Name
--------   ------
westus2     7_8-gen2
westus2     8.0
westus2     8_0-gen2
westus2     8_1
westus2     8_1-gen2
westus2     8_2
westus2     8_2-gen2
```

