#!/bin/bash

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
# See the License for the specific 

if [ ! -f /home/$CLUSTER_USERNAME/.fluo-cluster/configured ]; then
  sudo bash -c "cat $CONF_DIR/hosts/append_to_hosts >> /etc/hosts"
  cat $CONF_DIR/ssh_config >> /home/$CLUSTER_USERNAME/.ssh/config
  chmod 600 /home/$CLUSTER_USERNAME/.ssh/config
  cat $CONF_DIR/bashrc >> /home/$CLUSTER_USERNAME/.bashrc
  sudo bash -c "echo 'vm.swappiness = 0' >> /etc/sysctl.conf"
  sudo bash -c "cat $CONF_DIR/limits.conf >> /etc/security/limits.conf"
  sudo sed -i "s/localhost.localdomain/$1/g" /etc/sysconfig/network
  mkdir /home/$CLUSTER_USERNAME/.fluo-cluster
  touch /home/$CLUSTER_USERNAME/.fluo-cluster/configured
  echo "`hostname` - Configured $1.  Rebooting..."
  sudo reboot
else
  echo "`hostname` - Already configured $1"
fi
