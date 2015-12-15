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

# Exit if any command fails
set -e

if [ ! -f /home/$CLUSTER_USERNAME/.fluo-cluster/configured ]; then

  if [ "$1" == "--use-config" ]; then
    IP_ADDR=`hostname -I`
    CONF_HOSTS=$CONF_DIR/hosts/configure
    HOST=`grep -w $IP_ADDR $CONF_HOSTS | cut -d ' ' -f 2`
    NUM_EPHEMERAL=`grep -w $IP_ADDR $CONF_HOSTS | cut -d ' ' -f 3`
    if [ -z "$HOST" ]; then
      echo "ERROR - The IP addr $IP_ADDR was not found in $CONF_HOSTS so `hostname` will not be configured"
      exit 1
    fi
  else
    HOST=$1
    NUM_EPHEMERAL=$2
  fi

  : ${HOST?"HOST must be set"}
  : ${NUM_EPHEMERAL?"NUM_EPHEMERAL must be set"}
  : ${CONF_DIR?"CONF_DIR must be set"}
  : ${SSH_DIR?"SSH_DIR must be set"}
  : ${CLUSTER_USERNAME?"CLUSTER_USERNAME must be set"}
  : ${HOME_DIR?"HOME_DIR must be set"}

  echo "`hostname`: Configuring $HOST with $NUM_EPHEMERAL drives"
  sudo bash -c "cat $CONF_DIR/hosts/append_to_hosts >> /etc/hosts"
  cat $CONF_DIR/ssh_config >> $SSH_DIR/config
  chmod 600 $SSH_DIR/config
  if [ -f $CONF_DIR/keys ]; then
    cat $CONF_DIR/keys >> $SSH_DIR/authorized_keys
  fi
  cat $SSH_DIR/id_rsa.pub >> $SSH_DIR/authorized_keys
  cat $CONF_DIR/bashrc >> /home/$CLUSTER_USERNAME/.bashrc
  sudo bash -c "echo 'vm.swappiness = 0' >> /etc/sysctl.conf"
  sudo bash -c "cat $CONF_DIR/limits.conf >> /etc/security/limits.conf"
  sudo rm /etc/security/limits.d/20-nproc.conf
  sudo hostnamectl set-hostname $HOST
  sudo bash -c "echo 'preserve_hostname: true' >> /etc/cloud/cloud.cfg"

  # Need g++ to build accumulo native libs
  sudo yum install -q -y gcc-c++

  # Settings to resolve network issues on AWS while running Spark (see FLUO-DEPLOY-83)
  sudo cp $CONF_DIR/ifup-local /sbin/ifup-local

  # Mount ephermal devices...
  sudo umount /mnt
  sudo mkdir /media/ephemeral0
  sudo sed -i 's#/mnt\tauto\tdefaults,nofail,comment=cloudconfig#/media/ephemeral0\tauto\tdefaults,nofail,noatime,nodiratime,comment=cloudconfig#g' /etc/fstab 
  sudo mount /media/ephemeral0
  c="c"
  for i in $(seq 1 $((NUM_EPHEMERAL-1)))
  do
    sudo mkdir /media/ephemeral$i
    sudo bash -c "echo '/dev/xvd$c  /media/ephemeral$i  auto  defaults,nofail,noatime,nodiratime,comment=cloudconfig  0  2' >> /etc/fstab"
    c=$(echo $c | tr 'a-z' 'b-z')
    sudo mount /media/ephemeral$i
  done

  # Make ephemeral drives writable
  for i in $(seq 0 $((NUM_EPHEMERAL-1)))
  do
    sudo chown $CLUSTER_USERNAME /media/ephemeral$i
  done

  mkdir $HOME_DIR/.fluo-cluster
  touch $HOME_DIR/.fluo-cluster/configured
  echo "`hostname`: Configured $HOST.  Rebooting..."
  sudo reboot
else
  echo "`hostname`: Already configured"
fi
