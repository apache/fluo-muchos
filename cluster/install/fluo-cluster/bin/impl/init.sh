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

SSH_OPTS=(-tt -o 'StrictHostKeyChecking no' -A)

set -e

echo "Initializing cluster"

echo "Confirming that nothing running on cluster"
$BIN_DIR/fluo-cluster kill &> /dev/null

echo "Removing any previous data"
pssh -i -h $CONF_DIR/hosts/all_hosts "rm -rf /media/ephemeral*/zoo*  /media/ephemeral*/hadoop* /media/ephemeral*/yarn* /media/ephemeral*/influxdb /media/ephemeral*/grafana"

echo "Installing all services on cluster"
pssh -p 10 -x "-tt -o 'StrictHostKeyChecking no'" -t 300 -i -h $CONF_DIR/hosts/all_hosts "$BIN_DIR/fluo-cluster install --use-config"
echo "Finished installing all services on cluster"

echo "Setting up myid file on each zookeeper server"
while read line; do
  IFS=' ' read -ra ARR <<< "$line"
  HOST=${ARR[0]}
  ID=${ARR[1]}
  echo "`hostname`: Setting zookeeper myid to $ID on $HOST"
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$HOST "mkdir -p $DATA_DIR/zookeeper; echo $ID > $DATA_DIR/zookeeper/myid" < /dev/null
done < $CONF_DIR/hosts/zookeeper_ids

echo "Starting hadoop"
ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$NAMENODE_HOST $HADOOP_PREFIX/bin/hdfs namenode -format
$BIN_DIR/fluo-cluster start hadoop

echo "Starting zookeeper"
$BIN_DIR/fluo-cluster start zookeeper

echo "Starting accumulo"
ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$ACCUMULOMASTER_HOST "source $CONF_DIR/env.sh; $ACCUMULO_HOME/bin/accumulo init --clear-instance-name --instance-name $ACCUMULO_INSTANCE --password $ACCUMULO_PASSWORD"
$BIN_DIR/fluo-cluster start accumulo

echo "Starting spark history server" 
$HADOOP_PREFIX/bin/hdfs dfs -mkdir -p /spark/history
$BIN_DIR/fluo-cluster start spark

if [[ "$SETUP_METRICS" = "true" ]]; then
  echo "Starting metrics (InfluxDB+Grafana)"
  $BIN_DIR/fluo-cluster start metrics
fi

echo "Cluster initialization is finished"
