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
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$NAMENODE_HOST $HADOOP_PREFIX/sbin/start-dfs.sh
  echo "$NAMENODE_HOST: HDFS started"
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$RESOURCEMANAGER_HOST $HADOOP_PREFIX/sbin/start-yarn.sh
  echo "$RESOURCEMANAGER_HOST: YARN started"
  ;;
zookeeper)
  for host in `cat $CONF_DIR/hosts/zookeepers`; do
    ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$host "export ZOO_LOG_DIR=$ZOOKEEPER_HOME; $ZOOKEEPER_HOME/bin/zkServer.sh start"
    echo "$host: Zookeeper started"
  done
  ;;
accumulo)
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$ACCUMULOMASTER_HOST $ACCUMULO_HOME/bin/start-all.sh
  echo "$ACCUMULOMASTER_HOST: Accumulo started"
  ;;
spark)
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$RESOURCEMANAGER_HOST $SPARK_INSTALL/sbin/start-history-server.sh
  echo "$RESOURCEMANAGER_HOST: Spark HistoryServer started"
  ;;
metrics)
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$METRICS_SERVER "nohup $INFLUXDB_INSTALL/bin/influxd -config $INFLUXDB_INSTALL/influxdb.conf &> $INFLUXDB_INSTALL/influxdb.log &"
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$METRICS_SERVER "nohup $GRAFANA_INSTALL/bin/grafana-server -homepath=$GRAFANA_INSTALL &> $GRAFANA_INSTALL/grafana.log &"
  sleep 10
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$METRICS_SERVER $INFLUXDB_INSTALL/bin/influx -execute "CREATE USER fluo WITH PASSWORD 'secret' WITH ALL PRIVILEGES"
  sleep 10
  retcode=1
  while [ $retcode != 0 ];  do
    URL=http://admin:admin@"$METRICS_SERVER":3000/api/datasources 
    curl $URL -X POST -H 'Content-Type: application/json;charset=UTF-8' --data-binary `cat $CONF_DIR/grafana-fluo-datasource.json`
    retcode=$?
    if [ $retcode != 0 ]; then
      echo "Failed to add Grafana data source.  Retrying in 5 sec.."
      sleep 5
    fi
  done
  retcode=1
  while [ $retcode != 0 ];  do
    URL=http://admin:admin@"$METRICS_SERVER":3000/api/datasources 
    curl $URL -X POST -H 'Content-Type: application/json;charset=UTF-8' --data-binary `cat $CONF_DIR/grafana-cluster-datasource.json`
    retcode=$?
    if [ $retcode != 0 ]; then
      echo "Failed to add Grafana data source.  Retrying in 5 sec.."
      sleep 5
    fi
  done 
  ;;
*)
  echo -e "Usage: fluo-cluster start <argument>\n"
  echo -e "Possible arguments:\n"
  echo "  hadoop      Starts Hadoop"
  echo "  zookeeper   Starts Zookeeper"
  echo "  accumulo    Starts Accumulo"
  exit 1
esac
