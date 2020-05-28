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

from muchos.config import ExistingDeployConfig


def test_existing_cluster():
    c = ExistingDeployConfig(
        "muchos",
        "../conf/muchos.props.example",
        "../conf/hosts/example/example_cluster",
        "../conf/checksums",
        "../conf/templates",
        "mycluster",
    )
    c.cluster_type = "existing"
    assert c.get_cluster_type() == "existing"
    assert c.node_type_map() == {}
    assert c.mount_root() == "/var/data"
    assert c.worker_data_dirs() == ["/var/data1", "/var/data2", "/var/data3"]
    assert c.default_data_dirs() == ["/var/data1", "/var/data2", "/var/data3"]
    assert c.metrics_drive_ids() == ["var-data1", "var-data2", "var-data3"]
    assert c.shutdown_delay_minutes() == "0"
