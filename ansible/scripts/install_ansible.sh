#!/bin/bash
#
# Licensed to the Apache Software Foundation (ASF) under one or more contributor license
# agreements. See the NOTICE file distributed with this work for additional information regarding
# copyright ownership. The ASF licenses this file to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the License. You may obtain a
# copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing permissions and limitations under
# the License.
#


bin=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
base_dir=$( cd "$( dirname "$bin" )" && pwd )

set -e

# enable yum epel repo
rpm -q --quiet epel-release || sudo yum install -q -y epel-release

# install ansible
rpm -q --quiet ansible || sudo yum install -q -y ansible

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
