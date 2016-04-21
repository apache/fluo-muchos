#!/bin/bash

bin=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
base_dir=$( cd "$( dirname "$bin" )" && pwd )

set -e

# enable yum epel repo
rpm -q --quiet epel-release || sudo yum install -q -y epel-release

# install ansible
rpm -q --quiet ansible || sudo yum install -q -y ansible1.9

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
