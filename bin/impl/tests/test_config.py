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
  c = DeployConfig("fluo-deploy", '../../conf/fluo-deploy.props.example', '../../conf/hosts/example/example_cluster', 'mycluster')
  assert c.get('ec2', 'default_instance_type') == 'm3.large'
  assert c.get('ec2', 'worker_instance_type') == 'm3.large'
  assert c.num_ephemeral('worker1') == 1
  assert c.num_ephemeral('worker1') == c.worker_num_ephemeral()
  assert c.get('ec2', 'region') == 'us-east-1'
  assert c.has_option('ec2', 'vpc_id') == False
  assert c.has_option('ec2', 'subnet_id') == False
  assert c.get('ec2', 'key_name') == 'my_aws_key'
  assert c.instance_tags() == {}
  assert len(c.nodes()) == 7
  assert c.get_node('leader1') == ['namenode', 'zookeeper', 'fluo']
  assert c.get_node('worker1') == ['worker']
  assert c.get_node('worker2') == ['worker']
  assert c.get_node('worker3') == ['worker']
  assert c.has_service('fluo')
  assert c.get_service_hostnames('worker') == ['worker1', 'worker2', 'worker3']
  assert c.get_service_hostnames('zookeeper') == ['leader1', 'leader2', 'leader3']
  assert c.get_hosts() == {'leader2': ('10.0.0.1', None), 'leader3': ('10.0.0.2', None), 'leader1': ('10.0.0.0', '23.0.0.0'),
                           'worker1': ('10.0.0.3', None), 'worker3': ('10.0.0.5', None), 'worker2': ('10.0.0.4', None)}
  assert c.get_public_ip('leader1') == '23.0.0.0'
  assert c.get_private_ip('leader1') == '10.0.0.0'
  assert c.cluster_name == 'mycluster'
  assert c.get('general', 'apache_mirror') == 'http://www.gtlib.gatech.edu/pub/apache'
  assert c.version("accumulo") == '1.6.4'
  assert c.version("fluo") == '1.0.0-beta-2-SNAPSHOT'
  assert c.version("hadoop") == '2.7.0'
  assert c.version("zookeeper") == '3.4.7'
  assert c.get_service_private_ips("worker") == ['10.0.0.3', '10.0.0.4', '10.0.0.5']
  assert c.zookeeper_connect() == "leader1,leader2,leader3"
  assert c.get('general', 'proxy_hostname') == "leader1"
  assert c.proxy_public_ip() == "23.0.0.0"
  assert c.proxy_private_ip() == "10.0.0.0"
  assert c.get('general', 'cluster_basedir') == "/home/centos"
  assert c.get('general', 'cluster_user') == "centos"
  assert c.get_non_proxy() == [('10.0.0.1', 'leader2'), ('10.0.0.2', 'leader3'), ('10.0.0.3', 'worker1'), ('10.0.0.4', 'worker2'), ('10.0.0.5', 'worker3')]
  assert c.get_host_services() == [('leader1', 'namenode zookeeper fluo'), ('leader2', 'resourcemanager zookeeper'), ('leader3', 'accumulomaster zookeeper'),
                                   ('metrics', 'metrics'), ('worker1', 'worker'), ('worker2', 'worker'), ('worker3', 'worker')]
  assert c.get_image_id('m3.large') == 'ami-61bbf104'
  assert c.get('ec2', 'aws_access_key') == 'access_key'
  assert c.get('ec2', 'aws_secret_key') == 'secret_key'
