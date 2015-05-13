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
  HOST=$1
  NUM_EPHEMERAL=$2

  sudo bash -c "cat $CONF_DIR/hosts/append_to_hosts >> /etc/hosts"
  cat $CONF_DIR/ssh_config >> /home/$CLUSTER_USERNAME/.ssh/config
  chmod 600 /home/$CLUSTER_USERNAME/.ssh/config
  if [ -f $CONF_DIR/keys ]; then
    cat $CONF_DIR/keys >> /home/$CLUSTER_USERNAME/.ssh/authorized_keys
  fi
  ssh $PROXY_HOST cat /home/$CLUSTER_USERNAME/.ssh/id_rsa.pub >> /home/$CLUSTER_USERNAME/.ssh/authorized_keys
  scp $CLUSTER_USERNAME@$PROXY_HOST:.ssh/id_rsa /home/$CLUSTER_USERNAME/.ssh/
  cat $CONF_DIR/bashrc >> /home/$CLUSTER_USERNAME/.bashrc
  sudo bash -c "echo 'vm.swappiness = 0' >> /etc/sysctl.conf"
  sudo bash -c "cat $CONF_DIR/limits.conf >> /etc/security/limits.conf"
  sudo sed -i "s/localhost.localdomain/$HOST/g" /etc/sysconfig/network

  #need g++ to build accumulo native libs
  sudo yum install -q -y gcc-c++

  #mount ephermal devices... 
  sudo sed -i 's/defaults,nofail,comment=cloudconfig/defaults,nofail,noatime,nodiratime,comment=cloudconfig/g' /etc/fstab
  c="c"
  for i in $(seq 1 $((NUM_EPHEMERAL-1)))
  do
    sudo mkdir /media/ephemeral$i
    sudo bash -c "echo '/dev/xvd$c  /media/ephemeral$i  auto  defaults,nofail,noatime,nodiratime,comment=cloudconfig  0  2' >> /etc/fstab"
    c=$(echo $c | tr 'a-z' 'b-z')
    sudo mount /media/ephemeral$i
  done

  #make ephemeral drives writable
  for i in $(seq 0 $((NUM_EPHEMERAL-1)))
  do
    sudo chown $CLUSTER_USERNAME /media/ephemeral$i
  done

  mkdir /home/$CLUSTER_USERNAME/.fluo-cluster
  touch /home/$CLUSTER_USERNAME/.fluo-cluster/configured
  echo "`hostname`: Configured $HOST.  Rebooting..."
  sudo reboot
else
  echo "`hostname`: Already configured $HOST"
fi
