#!/usr/bin/python3
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

# flake8: noqa
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import six


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: azure_rm_virtualmachinescaleset_nic_list_facts

version_added: "2.9"

short_description: Get network interface facts for a VMSS

description:
    - Get a list of all network interfaces for a virtual machine scale set

options:
    vmss_name:
        description:
            - Name of the virtual machine scale set.
        required: true
    resource_group:
        description:
            - Name of the resource group containing the virtual machine scale set.
        required: true

extends_documentation_fragment:
    - azure

'''

EXAMPLES = '''
    - name: Get all network interfaces in a virtual machine scale set
      azure_rm_virtualmachinescaleset_nic_list_facts:
        resource_group: myResourceGroup
        vmss_name: myvmss
'''

RETURN = '''
azure_networkinterfaces:
    description: List of network interface dicts.
    returned: always
    type: list
    example: [{
        "dns_settings": {
            "applied_dns_servers": [],
            "dns_servers": [],
            "internal_dns_name_label": null,
            "internal_fqdn": null
        },
        "enable_ip_forwarding": false,
        "etag": 'W/"59726bfc-08c4-44ed-b900-f6a559876a9d"',
        "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroup/myResourceGroup/providers/Microsoft.Network/networkInterfaces/nic003",
        "ip_configuration": {
            "name": "default",
            "private_ip_address": "10.10.0.4",
            "private_ip_allocation_method": "Dynamic",
            "public_ip_address": {
                "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroup/myResourceGroup/providers/Microsoft.Network/publicIPAddresses/publicip001",
                "name": "publicip001"
            },
            "subnet": {
                "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroup/myResourceGroup/providers/Microsoft.Network/virtualNetworks/vnet001/subnets/subnet001",
                "name": "subnet001",
                "virtual_network_name": "vnet001"
            }
        },
        "location": "westus",
        "mac_address": null,
        "name": "nic003",
        "network_security_group": {
            "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroup/myResourceGroup/providers/Microsoft.Network/networkSecurityGroups/secgroup001",
            "name": "secgroup001"
        },
        "primary": null,
        "provisioning_state": "Succeeded",
        "tags": {},
        "type": "Microsoft.Network/networkInterfaces"
    }]
networkinterfaces:
    description: List of network interface dict, the dict contains parameters can be passed to C(azure_rm_networkinterface) module.
    type: list
    returned: always
    contains:
        id:
            description:
                - Id of the network interface.
        resource_group:
            description:
                - Name of a resource group where the network interface exists.
        name:
            description:
                - Name of the network interface.
        location:
            description:
                - Azure location.
        virtual_network:
            description:
                - An existing virtual network with which the network interface will be associated.
                - It is a dict which contains C(name) and C(resource_group) of the virtual network.
        subnet:
            description:
                - Name of an existing subnet within the specified virtual network.
        tags:
            description:
                - Tags of the network interface.
        ip_configurations:
            description:
                - List of ip configuration if contains mutilple configuration.
            contains:
                name:
                    description:
                        - Name of the ip configuration.
                private_ip_address:
                    description:
                        - Private ip address for the ip configuration.
                private_ip_allocation_method:
                    description:
                        - private ip allocation method.
                public_ip_address:
                    description:
                        - Name of the public ip address. None for disable ip address.
                public_ip_allocation_method:
                    description:
                        - public ip allocation method.
                load_balancer_backend_address_pools:
                    description:
                        - List of an existing load-balancer backend address pool id to associate with the network interface.
                primary:
                    description:
                        - Whether the ip configuration is the primary one in the list.
                application_security_groups:
                    description:
                        - List of Application security groups.
                    sample: /subscriptions/<subsid>/resourceGroups/<rg>/providers/Microsoft.Network/applicationSecurityGroups/myASG
        enable_accelerated_networking:
            description:
                - Specifies whether the network interface should be created with the accelerated networking feature or not
        create_with_security_group:
            description:
                - Specifies whether a default security group should be be created with the NIC. Only applies when creating a new NIC.
            type: bool
        security_group:
            description:
                - A security group resource ID with which to associate the network interface.
        enable_ip_forwarding:
            description:
                - Whether to enable IP forwarding
        dns_servers:
            description:
                - Which DNS servers should the NIC lookup
                - List of IP's
        mac_address:
            description:
                - The MAC address of the network interface.
        provisioning_state:
            description:
                - The provisioning state of the network interface.
        dns_settings:
            description:
                - The DNS settings in network interface.
            contains:
                dns_servers:
                    description: List of DNS servers IP addresses.
                applied_dns_servers:
                    description:
                        - If the VM that uses this NIC is part of an Availability Set, then this list will have the union of all DNS servers
                          from all NICs that are part of the Availability Set. This property is what is configured on each of those VMs.
                internal_dns_name_label:
                    description: Relative DNS name for this NIC used for internal communications between VMs in the same virtual network.
                internal_fqdn:
                    description: Fully qualified DNS name supporting internal communications between VMs in the same virtual network.
'''  # NOQA
try:
    from msrestazure.azure_exceptions import CloudError
    from azure.common import AzureMissingResourceHttpError, AzureHttpError
except Exception:
    # This is handled in azure_rm_common
    pass

from ansible.module_utils.azure_rm_common import AzureRMModuleBase, azure_id_to_dict


AZURE_OBJECT_CLASS = 'NetworkInterface'


class AzureRMVirtualMachineScaleSetNetworkInterfaceFacts(AzureRMModuleBase):

    def __init__(self):

        self.module_arg_spec = dict(
            vmss_name=dict(type='str', required=True),
            resource_group=dict(type='str', required=True),
            tags=dict(type='list')
        )

        self.results = dict(
            changed=False,
            networkinterfaces=[]
        )

        self.vmss_name = None
        self.resource_group = None
        self.tags = None

        super(AzureRMVirtualMachineScaleSetNetworkInterfaceFacts,
              self).__init__(self.module_arg_spec,
                             supports_tags=False,
                             facts_module=True
                             )

    def exec_module(self, **kwargs):

        for key in self.module_arg_spec:
            setattr(self, key, kwargs[key])

        if not (self.vmss_name and self.resource_group):
            self.fail("Parameter error: resource group and name are required parameters.")

        networkinterfaces = []

        networkinterfaces = self.list_nics()

        self.results['networkinterfaces'] = self._promote_properties(self.serialize_nics(networkinterfaces))
        return self.results

    def list_nics(self):
        self.log('Get properties for {0}'.format(self.vmss_name))
        item = None
        try:
            return self.network_client.network_interfaces.list_virtual_machine_scale_set_network_interfaces(self.resource_group, self.vmss_name)
        except Exception as exc:
            self.fail("Error fetching nic list - {0}".format(str(exc)))


    def serialize_nics(self, raws):
        return [self.serialize_obj(item, AZURE_OBJECT_CLASS) for item in raws] if raws else []


    def _promote_properties(self, obj):
        if isinstance(obj, list):
            return [self._promote_properties(i) for i in obj]

        if isinstance(obj, dict):
            for k,v in six.iteritems(obj):
                if isinstance(v, (list, dict)):
                    obj.update({k: self._promote_properties(v)})

            if isinstance(obj.get("properties"), dict):
                properties = obj.pop("properties")
                obj.update(properties)

        return obj


def main():
    AzureRMVirtualMachineScaleSetNetworkInterfaceFacts()


if __name__ == '__main__':
    main()
