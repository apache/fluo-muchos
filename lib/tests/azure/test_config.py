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

from muchos.config.azure import AzureDeployConfig


def test_azure_cluster():
    c = AzureDeployConfig(
        "muchos",
        "../conf/muchos.props.example",
        "../conf/hosts/example/example_cluster",
        "../conf/checksums",
        "../conf/templates",
        "mycluster",
    )

    # since we are sharing a single muchos.props.example file, we need to stub
    # the cluster type to be azure (as the file itself has a default of ec2)

    c.cluster_type = "azure"

    assert c.checksum_ver("fluo", "1.2.0") == (
        "sha256:"
        "037f89cd2bfdaf76a1368256c52de46d6b9a85c9c1bfc776ec4447d02c813fb2"
    )
    assert c.checksum("accumulo") == (
        "sha512:"
        "1a27a144dc31f55ccc8e081b6c1bc6cc0362a8391838c53c166cb45291ff8f35"
        "867fd8e4729aa7b2c540f8b721f8c6953281bf589fc7fe320e4dc4d20b87abc4"
    )
    assert c.get("azure", "vm_sku") == "Standard_D8s_v3"
    assert c.get("azure", "data_disk_sku") == "Standard_LRS"
    assert c.user_home() == "/home/" + c.get("general", "cluster_user")
    assert c.mount_root() == "/var/data"
    assert c.use_multiple_vmss() is False
    assert c.worker_data_dirs() == ["/var/data1", "/var/data2", "/var/data3"]
    assert c.default_data_dirs() == ["/var/data1", "/var/data2", "/var/data3"]
    assert c.metrics_drive_ids() == ["var-data1", "var-data2", "var-data3"]
    assert c.shutdown_delay_minutes() == "0"
    assert c.mounts(2) == ["/var/data0", "/var/data1"]
    assert c.node_type("worker1") == "worker"
    assert c.node_type("leader1") == "default"
    assert c.has_option("azure", "resource_group")
    assert c.has_option("azure", "vnet")
    assert c.has_option("azure", "vnet_cidr")
    assert c.has_option("azure", "subnet")
    assert c.has_option("azure", "subnet_cidr")
    assert c.has_option("azure", "numnodes")
    assert c.has_option("azure", "location")
    assert len(c.nodes()) == 6
    assert c.get_node("leader1") == [
        "namenode",
        "resourcemanager",
        "accumulomaster",
        "zookeeper",
    ]
    assert c.get_node("leader2") == ["metrics"]
    assert c.get_node("worker1") == ["worker", "swarmmanager"]
    assert c.get_node("worker2") == ["worker"]
    assert c.get_node("worker3") == ["worker"]
    assert c.has_service("accumulomaster")
    assert not c.has_service("fluo")
    assert c.get_service_hostnames("worker") == [
        "worker1",
        "worker2",
        "worker3",
        "worker4",
    ]
    assert c.get_service_hostnames("zookeeper") == ["leader1"]
    assert c.get_hosts() == {
        "leader2": ("10.0.0.1", None),
        "leader1": ("10.0.0.0", "23.0.0.0"),
        "worker1": ("10.0.0.2", None),
        "worker3": ("10.0.0.4", None),
        "worker2": ("10.0.0.3", None),
        "worker4": ("10.0.0.5", None),
    }
    assert c.get_public_ip("leader1") == "23.0.0.0"
    assert c.get_private_ip("leader1") == "10.0.0.0"
    assert c.cluster_name == "mycluster"
    assert c.get_cluster_type() == "azure"
    assert c.version("accumulo").startswith("2.")
    assert c.version("fluo").startswith("1.")
    assert c.version("hadoop").startswith("3.")
    assert c.version("zookeeper").startswith("3.")
    assert c.get_service_private_ips("worker") == [
        "10.0.0.2",
        "10.0.0.3",
        "10.0.0.4",
        "10.0.0.5",
    ]
    assert c.get("general", "proxy_hostname") == "leader1"
    assert c.proxy_public_ip() == "23.0.0.0"
    assert c.proxy_private_ip() == "10.0.0.0"
    assert c.get("general", "cluster_user") == (
        c.get("general", "cluster_group")
    )
    assert c.get_non_proxy() == [
        ("10.0.0.1", "leader2"),
        ("10.0.0.2", "worker1"),
        ("10.0.0.3", "worker2"),
        ("10.0.0.4", "worker3"),
        ("10.0.0.5", "worker4"),
    ]
    assert c.get_host_services() == [
        ("leader1", "namenode resourcemanager accumulomaster zookeeper"),
        ("leader2", "metrics"),
        ("worker1", "worker swarmmanager"),
        ("worker2", "worker"),
        ("worker3", "worker"),
        ("worker4", "worker"),
    ]

    # TODO: add test cases for the validations
