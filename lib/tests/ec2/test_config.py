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

from muchos.config.ec2 import Ec2DeployConfig


def test_ec2_cluster():
    c = Ec2DeployConfig(
        "muchos",
        "../conf/muchos.props.example",
        "../conf/hosts/example/example_cluster",
        "../conf/checksums",
        "../conf/templates",
        "mycluster",
    )
    assert c.checksum_ver("fluo", "1.2.0") == (
        "sha256:"
        "037f89cd2bfdaf76a1368256c52de46d6b9a85c9c1bfc776ec4447d02c813fb2"
    )
    assert c.checksum("accumulo") == (
        "sha512:"
        "b443839443a9f5098b55bc5c54be10c11fedbaea554ee6cd42eaa9311068c70b"
        "d611d7fc67698c91ec73da0e85b9907aa72b98d5eb4d49ea3a5d51b0c6c5785f"
    )
    assert c.get("ec2", "default_instance_type") == "m5d.large"
    assert c.get("ec2", "worker_instance_type") == "m5d.large"
    assert c.get("ec2", "aws_ami").startswith("ami-")
    assert c.user_home() == "/home/" + c.get("general", "cluster_user")
    assert c.max_ephemeral() == 1
    assert c.mount_root() == "/media/ephemeral"
    assert c.fstype() == "ext4"
    assert c.force_format() == "no"
    assert c.worker_data_dirs() == ["/media/ephemeral0"]
    assert c.default_data_dirs() == ["/media/ephemeral0"]
    assert c.metrics_drive_ids() == ["media-ephemeral0"]
    assert c.shutdown_delay_minutes() == "0"
    assert c.mounts(2) == ["/media/ephemeral0", "/media/ephemeral1"]
    assert c.node_type_map() == {
        "default": {
            "mounts": ["/media/ephemeral0"],
            "devices": ["/dev/nvme1n1"],
        },
        "worker": {
            "mounts": ["/media/ephemeral0"],
            "devices": ["/dev/nvme1n1"],
        },
    }
    assert c.node_type("worker1") == "worker"
    assert c.node_type("leader1") == "default"
    assert not c.has_option("ec2", "vpc_id")
    assert not c.has_option("ec2", "subnet_id")
    assert c.get("ec2", "key_name") == "my_aws_key"
    assert c.instance_tags() == {}
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
    assert c.get_cluster_type() == "ec2"
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


def test_case_sensitive():
    c = Ec2DeployConfig(
        "muchos",
        "../conf/muchos.props.example",
        "../conf/hosts/example/example_cluster",
        "../conf/checksums",
        "../conf/templates",
        "mycluster",
    )
    assert c.has_option("ec2", "default_instance_type")
    assert not c.has_option("ec2", "Default_instance_type")
    c.set("nodes", "CamelCaseWorker", "worker,fluo")
    c.init_nodes()
    assert c.get_node("CamelCaseWorker") == ["worker", "fluo"]


def test_ec2_cluster_template():
    c = Ec2DeployConfig(
        "muchos",
        "../conf/muchos.props.example",
        "../conf/hosts/example/example_cluster",
        "../conf/checksums",
        "../conf/templates",
        "mycluster",
    )

    c.set("ec2", "cluster_template", "example")
    c.init_template("../conf/templates")
    # init_template already calls validate_template, so just ensure that
    # we've loaded all the expected dictionary items from the example
    assert "accumulomaster" in c.cluster_template_d
    assert "client" in c.cluster_template_d
    assert "metrics" in c.cluster_template_d
    assert "namenode" in c.cluster_template_d
    assert "resourcemanager" in c.cluster_template_d
    assert "worker" in c.cluster_template_d
    assert "zookeeper" in c.cluster_template_d
    assert "devices" in c.cluster_template_d
