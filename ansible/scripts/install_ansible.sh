#!/bin/bash
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


bin=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
base_dir=$( cd "$( dirname "$bin" )" && pwd )

set -e

# enable yum epel repo
is_installed_epel_release="rpm -q --quiet epel-release"
install_epel_release="sudo yum install -q -y epel-release"
for i in {1..10}; do ($is_installed_epel_release || $install_epel_release) && break || sleep 15; done

# install ansible
is_installed_ansible="rpm -q --quiet ansible"
install_ansible="sudo yum install -q -y ansible"
for i in {1..10}; do ($is_installed_ansible || $install_ansible) && break || sleep 15; done

# setup user-specific ansible configuration
if [ ! -h ~/.ansible.cfg ]; then
  cd ~/
  rm -f .ansible.cfg
  ln -s $base_dir/conf/ansible.cfg .ansible.cfg
fi

# setup ansible hosts
if [ ! -h /etc/ansible/hosts ]; then
  cd /etc/ansible
  sudo rm -f hosts
  sudo ln -s $base_dir/conf/hosts hosts
fi

# install lxml as it is a dependency for the maven_artifact Ansible module
sudo yum install -q -y python-lxml

# install jq to ease JSON parsing on the proxy
sudo yum install -y jq
