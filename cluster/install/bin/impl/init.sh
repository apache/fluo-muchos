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

$BIN_DIR/fluo-cluster kill &> /dev/null

while read line; do
  IFS=' ' read -ra ARR <<< "$line"
  HOST=${ARR[0]}
  SERVICES=${ARR[@]:1}
  echo "`hostname` - Installing services on $HOST: $SERVICES"
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$HOST $INSTALL_DIR/bin/fluo-cluster install $SERVICES < /dev/null
done < $CONF_DIR/hosts/all_with_services

for host in `cat $CONF_DIR/hosts/all`; do
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$host rm -rf $INSTALL_DIR/data
done

# Setup & Start Hadoop
NAMENODE_HOST=`cat $INSTALL_DIR/conf/hosts/namenode`
ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$NAMENODE_HOST $HADOOP_PREFIX/bin/hdfs namenode -format
$BIN_DIR/fluo-cluster start hadoop

# Setup & Start Zookeeper
$BIN_DIR/fluo-cluster start zookeeper

# Setup & Start Accumulo
ACCUMULO_HOST=`cat $INSTALL_DIR/conf/hosts/accumulomaster`
ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$ACCUMULO_HOST "source $CONF_DIR/env.sh; $ACCUMULO_HOME/bin/accumulo init --clear-instance-name --instance-name $ACCUMULO_INSTANCE --password $ACCUMULO_PASSWORD"
$BIN_DIR/fluo-cluster start accumulo
