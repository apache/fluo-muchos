# Copyright 2014 Fluo authors (see AUTHORS)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from fluo_deploy.config import DeployConfig

def test_defaults():
  c = DeployConfig("fluo-deploy", '../../conf/fluo-deploy.props.example', '../../conf/hosts/example_cluster', 'mycluster')
  assert c.default_instance_type() == 'm3.large'
  assert c.region() == 'us-east-1'
  assert c.vpc_id() == None
  assert c.subnet_id() == None
  assert c.key_name() == 'my_aws_key'
  assert c.instance_tags() == {}
  assert len(c.nodes()) == 4
  assert c.get_node('leader') == ('default', ['namenode', 'resourcemanager', 'accumulomaster', 'zookeeper', 'fluo'])
  assert c.get_node('worker1') == ('default', ['worker'])
  assert c.get_node('worker2') == ('default', ['worker'])
  assert c.get_node('worker3') == ('default', ['worker'])
  assert c.get_service_hostnames('worker') == ['worker1', 'worker2', 'worker3']
  assert c.get_service_hostnames('zookeeper') == ['leader']
  assert c.get_hosts() == {'worker1': ('10.0.0.1', '23.0.0.1'), 'worker3': ('10.0.0.3', None),
          'worker2': ('10.0.0.2', None), 'leader': ('10.0.0.0', '23.0.0.0')}
  assert c.get_public_ip('leader') == '23.0.0.0'
  assert c.get_private_ip('leader') == '10.0.0.0'
  assert c.cluster_name == 'mycluster'
  assert c.apache_mirror() == 'http://www.gtlib.gatech.edu/pub/apache'
  assert c.accumulo_version() == '1.6.1'
  assert c.fluo_version() == '1.0.0-beta-1-SNAPSHOT'
  assert c.hadoop_version() == '2.6.0'
  assert c.zookeeper_version() == '3.4.6'
  assert c.hadoop_prefix() == "/home/ec2-user/install/hadoop-2.6.0"
  assert c.data_dir() == "/home/ec2-user/install/data"
  assert c.cluster_tarballs_dir() == "/home/ec2-user/tarballs"
  assert c.accumulo_tarball() == "accumulo-1.6.1-bin.tar.gz"
  assert c.accumulo_path() == "fluo-deploy/cluster/tarballs/accumulo-1.6.1-bin.tar.gz"
  assert c.accumulo_url() == "http://www.gtlib.gatech.edu/pub/apache/accumulo/1.6.1/accumulo-1.6.1-bin.tar.gz"
  assert c.get_service_private_ips("worker") == ['10.0.0.1', '10.0.0.2', '10.0.0.3']
  assert c.zookeeper_connect() == "10.0.0.0:2181"
  assert c.leader_hostname() == "leader"
  assert c.leader_public_ip() == "23.0.0.0"
  assert c.leader_private_ip() == "10.0.0.0"
  assert c.cluster_base_dir() == "/home/ec2-user"
  assert c.cluster_username() == "ec2-user"
  assert c.configure_cluster() == "true"
  assert c.get_non_leaders() == [('10.0.0.1','worker1'), ('10.0.0.2','worker2'), ('10.0.0.3','worker3')]
  assert c.get_host_services() == [('10.0.0.0', 'namenode resourcemanager accumulomaster zookeeper fluo'), ('10.0.0.1', 'worker'), ('10.0.0.2', 'worker'), ('10.0.0.3', 'worker')]
