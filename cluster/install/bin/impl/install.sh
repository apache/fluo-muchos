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

RSYNC_OPTS=(-e "ssh -o 'StrictHostKeyChecking no'" --ignore-existing)

function install_accumulo() {
  if [ ! -d "$ACCUMULO_HOME" ]; then
    rsync "${RSYNC_OPTS[@]}" $CLUSTER_USERNAME@$LEADER_HOST:$TARBALLS_DIR/$ACCUMULO_TARBALL $TARBALLS_DIR
    tar -C $INSTALL_DIR -xzf $TARBALLS_DIR/$ACCUMULO_TARBALL
    cp $ACCUMULO_HOME/conf/templates/* $ACCUMULO_HOME/conf/
    cp $CONF_DIR/accumulo-site.xml $ACCUMULO_HOME/conf/
    cp $CONF_DIR/accumulo-env.sh $ACCUMULO_HOME/conf/
    cp $CONF_DIR/hosts/accumulomaster $ACCUMULO_HOME/conf/masters
    cp $CONF_DIR/hosts/accumulomaster $ACCUMULO_HOME/conf/gc
    cp $CONF_DIR/hosts/accumulomaster $ACCUMULO_HOME/conf/monitor
    cp $CONF_DIR/hosts/accumulomaster $ACCUMULO_HOME/conf/tracers
    cp $CONF_DIR/hosts/workers $ACCUMULO_HOME/conf/slaves
    echo "`hostname`: Accumulo installed"
  fi
}

function install_hadoop() {
  if [ ! -d "$HADOOP_PREFIX" ]; then
    rsync "${RSYNC_OPTS[@]}" $CLUSTER_USERNAME@$LEADER_HOST:$TARBALLS_DIR/$HADOOP_TARBALL $TARBALLS_DIR
    tar -C $INSTALL_DIR -xzf $TARBALLS_DIR/$HADOOP_TARBALL
    cp $CONF_DIR/core-site.xml $HADOOP_PREFIX/etc/hadoop/
    cp $CONF_DIR/hdfs-site.xml $HADOOP_PREFIX/etc/hadoop/
    cp $CONF_DIR/yarn-site.xml $HADOOP_PREFIX/etc/hadoop/
    cp $CONF_DIR/hosts/workers $HADOOP_PREFIX/etc/hadoop/slaves
    echo "`hostname`: Hadoop installed"
  fi
}

function install_zookeeper() {
  if [ ! -d "$ZOOKEEPER_HOME" ]; then
    rsync "${RSYNC_OPTS[@]}" $CLUSTER_USERNAME@$LEADER_HOST:$TARBALLS_DIR/$ZOOKEEPER_TARBALL $TARBALLS_DIR
    tar -C $INSTALL_DIR -xzf $TARBALLS_DIR/$ZOOKEEPER_TARBALL
    cp $CONF_DIR/zoo.cfg $ZOOKEEPER_HOME/conf/
    echo "`hostname`: Zookeeper installed"
  fi
}

function install_fluo() {
  if [ ! -d "$FLUO_HOME" ]; then
    rsync "${RSYNC_OPTS[@]}" $CLUSTER_USERNAME@$LEADER_HOST:$TARBALLS_DIR/$FLUO_TARBALL $TARBALLS_DIR
    tar -C $INSTALL_DIR -xzf $TARBALLS_DIR/$FLUO_TARBALL
    cp $FLUO_HOME/conf/examples/* $FLUO_HOME/conf/
    cp $CONF_DIR/fluo.properties $FLUO_HOME/conf/
    cp $CONF_DIR/fluo-env.sh $FLUO_HOME/conf/
    echo "`hostname`: Fluo installed"
  fi
}

for service in "$@"; do
  echo "`hostname`: Installing $service node"

  case "$service" in
    accumulomaster)
      install_accumulo
      install_hadoop
      install_zookeeper
      ;;
    namenode)
      install_hadoop
      ;;
    resourcemanager)
      install_hadoop
      ;;
    zookeeper)
      install_zookeeper
      ;;
    worker)
      install_accumulo
      install_hadoop
      install_zookeeper
      ;;
    fluo)
      install_fluo
      ;;
    *)
      echo "Unknown service: $service"
      exit 1
  esac
done
