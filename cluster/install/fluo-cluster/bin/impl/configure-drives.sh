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

impl=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
. "$impl"/../../conf/env.sh

# Exit if any command fails
set -e

IP_ADDR=`hostname -I`
CONF_HOSTS=$CONF_DIR/hosts/configure
HOST=`grep -w $IP_ADDR $CONF_HOSTS | cut -d ' ' -f 2`
NUM_EPHEMERAL=`grep -w $IP_ADDR $CONF_HOSTS | cut -d ' ' -f 3`

: ${HOST?"HOST must be set"}
: ${NUM_EPHEMERAL?"NUM_EPHEMERAL must be set"}
: ${CONF_DIR?"CONF_DIR must be set"}
: ${HOME_DIR?"HOME_DIR must be set"}
: ${CLUSTER_USERNAME?"CLUSTER_USERNAME must be set"}

FC_DIR=$HOME_DIR/.fluo-cluster
mkdir -p $FC_DIR

if [ ! -f $FC_DIR/hostname ]; then
  sudo hostnamectl set-hostname $HOST
  sudo bash -c "echo 'preserve_hostname: true' >> /etc/cloud/cloud.cfg"
  touch $FC_DIR/hostname
fi

# Mount ephermal devices...
if [ ! -f $FC_DIR/drives ]; then
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
  touch $FC_DIR/drives
fi
