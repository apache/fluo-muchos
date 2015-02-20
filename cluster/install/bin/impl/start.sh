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

case "$1" in
hadoop)
  NAMENODE_HOST=`cat $INSTALL_DIR/conf/hosts/namenode`
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$NAMENODE_HOST $HADOOP_PREFIX/sbin/start-dfs.sh
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$NAMENODE_HOST $HADOOP_PREFIX/sbin/start-yarn.sh
  echo "$NAMENODE_HOST: Hadoop started"
  ;;
zookeeper)
  for host in `cat $CONF_DIR/hosts/zookeepers`; do
    ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$host "export ZOO_LOG_DIR=$ZOOKEEPER_HOME; $ZOOKEEPER_HOME/bin/zkServer.sh start"
    echo "$host: Zookeeper started"
  done
  ;;
accumulo)
  ACCUMULO_HOST=`cat $INSTALL_DIR/conf/hosts/accumulomaster`
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$ACCUMULO_HOST $ACCUMULO_HOME/bin/start-all.sh
  echo "$ACCUMULO_HOST: Accumulo started"
  ;;
*)
  echo -e "Usage: fluo-cluster start <argument>\n"
  echo -e "Possible arguments:\n"
  echo "  hadoop      Starts Hadoop"
  echo "  zookeeper   Starts Zookeeper"
  echo "  accumulo    Starts Accumulo"
  exit 1
esac
