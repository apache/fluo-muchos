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

for host in `cat $CONF_DIR/hosts/all_hosts`; do
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$host rm -rf $INSTALL_DIR/data
done

while read line; do
  IFS=' ' read -ra ARR <<< "$line"
  HOST=${ARR[0]}
  SERVICES=${ARR[@]:1}
  echo "`hostname`: Installing services on $HOST: $SERVICES"
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$HOST $BIN_DIR/fluo-cluster install $SERVICES < /dev/null
done < $CONF_DIR/hosts/hosts_with_services

# Setup myid file on each zookeeper server
while read line; do
  IFS=' ' read -ra ARR <<< "$line"
  HOST=${ARR[0]}
  ID=${ARR[1]}
  echo "`hostname`: Setting zookeeper myid to $ID on $HOST"
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$HOST "mkdir -p $INSTALL_DIR/data/zookeeper; echo $ID > $INSTALL_DIR/data/zookeeper/myid" < /dev/null
done < $CONF_DIR/hosts/zookeeper_ids

# Setup & Start Hadoop
ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$NAMENODE_HOST $HADOOP_PREFIX/bin/hdfs namenode -format
$BIN_DIR/fluo-cluster start hadoop

# Setup & Start Zookeeper
$BIN_DIR/fluo-cluster start zookeeper

# Setup & Start Accumulo
ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$ACCUMULOMASTER_HOST "source $CONF_DIR/env.sh; $ACCUMULO_HOME/bin/accumulo init --clear-instance-name --instance-name $ACCUMULO_INSTANCE --password $ACCUMULO_PASSWORD"
$BIN_DIR/fluo-cluster start accumulo
