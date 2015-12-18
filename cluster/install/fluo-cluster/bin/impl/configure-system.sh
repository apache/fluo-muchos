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

: ${CONF_DIR?"CONF_DIR must be set"}
: ${SSH_DIR?"SSH_DIR must be set"}
: ${HOME_DIR?"HOME_DIR must be set"}

FC_DIR=$HOME_DIR/.fluo-cluster
mkdir -p $FC_DIR

if [ ! -f $FC_DIR/ssh ]; then
  sudo bash -c "cat $CONF_DIR/hosts/append_to_hosts >> /etc/hosts"
  cat $CONF_DIR/ssh_config >> $SSH_DIR/config
  chmod 600 $SSH_DIR/config
  if [ -f $CONF_DIR/keys ]; then
    cat $CONF_DIR/keys >> $SSH_DIR/authorized_keys
  fi
  cat $SSH_DIR/id_rsa.pub >> $SSH_DIR/authorized_keys
  touch $FC_DIR/ssh
fi

if [ ! -f $FC_DIR/system ]; then
  cat $CONF_DIR/bashrc >> $HOME_DIR/.bashrc
  sudo bash -c "echo 'vm.swappiness = 0' >> /etc/sysctl.conf"
  sudo sysctl -p
  sudo bash -c "cat $CONF_DIR/limits.conf >> /etc/security/limits.conf"
  sudo rm -f /etc/security/limits.d/20-nproc.conf
  # Settings to resolve network issues on AWS while running Spark (see FLUO-DEPLOY-83)
  sudo cp $CONF_DIR/ifup-local /sbin/ifup-local
  sudo /sbin/ifup-local eth0
  touch $FC_DIR/system
fi

# Need g++ to build accumulo native libs
if ! rpm -q --quiet gcc-c++ ; then
  sudo yum install -q -y gcc-c++
fi
