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

SSH_OPTS=(-o 'StrictHostKeyChecking no' -A)

# Download required tarballs
wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/zookeeper/zookeeper-$ZOOKEEPER_VERSION/$ZOOKEEPER_TARBALL
wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/accumulo/$ACCUMULO_VERSION/$ACCUMULO_TARBALL
wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/hadoop/common/hadoop-$HADOOP_VERSION/$HADOOP_TARBALL

# Push install directory to all hosts
for host in `cat $CONF_DIR/hosts/all_except_leader`; do
  echo "`hostname` - Copying scripts to $host"
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$host mkdir -p $TARBALLS_DIR
  scp $TARBALLS_DIR/install.tar.gz $CLUSTER_USERNAME@$host:$TARBALLS_DIR
  ssh $CLUSTER_USERNAME@$host "rm -rf $INSTALL_DIR; tar -C $BASE_DIR -xzf $TARBALLS_DIR/install.tar.gz"
done

$BIN_DIR/fluo-cluster kill &> /dev/null

$BIN_DIR/fluo-cluster configure
