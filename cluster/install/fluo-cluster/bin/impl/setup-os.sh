#!/usr/bin/env bash

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

echo "Cluster setup started"

rpm -q --quiet epel-release || sudo yum install -q -y epel-release
rpm -q --quiet wget || sudo yum install -q -y wget
rpm -q --quiet pssh || sudo yum install -q -y pssh

echo "Creating tarballs directory on all nodes"
pssh -x "-o 'StrictHostKeyChecking no'" -i -h $CONF_DIR/hosts/all_except_proxy "mkdir -p $TARBALLS_DIR"

echo "Copying scripts to all nodes"
pscp.pssh -h $CONF_DIR/hosts/all_except_proxy $TARBALLS_DIR/install.tar.gz $TARBALLS_DIR/install.tar.gz

echo "Installing scripts on all nodes"
pssh -i -h $CONF_DIR/hosts/all_except_proxy "rm -rf $INSTALL_DIR; tar -C $BASE_DIR -xzf $TARBALLS_DIR/install.tar.gz"

echo "Confirming that nothing is running on cluster"
$BIN_DIR/fluo-cluster kill &> /dev/null

if [ "$CONFIGURE_CLUSTER" == "true" ]; then
  echo "Configuring machines on cluster"
  if [ ! -f /home/$CLUSTER_USERNAME/.ssh/id_rsa ]; then
   ssh-keygen  -q -t rsa -N ''  -f /home/$CLUSTER_USERNAME/.ssh/id_rsa
  fi

  echo "Copying private key to all nodes"
  pscp.pssh -h $CONF_DIR/hosts/all_except_proxy $SSH_DIR/id_rsa $SSH_DIR/id_rsa
  echo "Copying public key to all nodes"
  pscp.pssh -h $CONF_DIR/hosts/all_except_proxy $SSH_DIR/id_rsa.pub $SSH_DIR/id_rsa.pub

  echo "Configuring non-proxy nodes"
  pssh -x "-tt -o 'StrictHostKeyChecking no'" -i -h $CONF_DIR/hosts/all_except_proxy "$BIN_DIR/fluo-cluster configure --use-config" || true

  echo "Configuring proxy"
  $BIN_DIR/fluo-cluster configure --use-config
else
  echo "User chose not to configure ~/.ssh/config, /etc/hosts, & ~/.bashrc on cluster"
fi
