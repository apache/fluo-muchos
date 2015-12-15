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

set -e

RSYNC_OPTS=(-e "ssh -o 'StrictHostKeyChecking no'" --ignore-existing)

function get_install() {
  tarball_filename=$1
  rsync "${RSYNC_OPTS[@]}" $CLUSTER_USERNAME@$PROXY_HOST:$TARBALLS_DIR/$tarball_filename $TARBALLS_DIR
  tar -C $INSTALL_DIR -xzf $TARBALLS_DIR/$tarball_filename
}

function install_accumulo() {
  if [ ! -d "$ACCUMULO_HOME" ]; then
    get_install $ACCUMULO_TARBALL
    cp $ACCUMULO_HOME/conf/templates/* $ACCUMULO_HOME/conf/
    cp $CONF_DIR/accumulo-site.xml $ACCUMULO_HOME/conf/
    cp $CONF_DIR/accumulo-env.sh $ACCUMULO_HOME/conf/
    cp $CONF_DIR/hosts/accumulomaster $ACCUMULO_HOME/conf/masters
    cp $CONF_DIR/hosts/accumulomaster $ACCUMULO_HOME/conf/gc
    cp $CONF_DIR/hosts/accumulomaster $ACCUMULO_HOME/conf/monitor
    cp $CONF_DIR/hosts/accumulomaster $ACCUMULO_HOME/conf/tracers
    cp $CONF_DIR/hosts/workers $ACCUMULO_HOME/conf/slaves
    $ACCUMULO_HOME/bin/build_native_library.sh
    echo "`hostname`: Accumulo installed"
  fi
}

function install_hadoop() {
  if [ ! -d "$HADOOP_PREFIX" ]; then
    get_install $HADOOP_TARBALL
    cp $CONF_DIR/hadoop/* $HADOOP_PREFIX/etc/hadoop/
    cp $CONF_DIR/core-site.xml $HADOOP_PREFIX/etc/hadoop/
    cp $CONF_DIR/hdfs-site.xml $HADOOP_PREFIX/etc/hadoop/
    cp $CONF_DIR/yarn-site.xml $HADOOP_PREFIX/etc/hadoop/
    cp $CONF_DIR/mapred-site.xml $HADOOP_PREFIX/etc/hadoop/
    cp $CONF_DIR/hosts/workers $HADOOP_PREFIX/etc/hadoop/slaves
    # The hadoop-ce directory needs to be placed at the Linux root as the container-executor has 
    # funky permission requirements that need to be applied to all parent directories.
    HCE_DIR=/hadoop-ce
    sudo rm -rf $HCE_DIR
    sudo mkdir -p $HCE_DIR/bin
    sudo mkdir -p $HCE_DIR/etc/hadoop
    sudo cp $HADOOP_PREFIX/bin/container-executor $HCE_DIR/bin
    sudo cp $CONF_DIR/container-executor.cfg $HCE_DIR/etc/hadoop/
    sudo chown -R root:$CLUSTER_USERNAME $HCE_DIR/
    sudo chmod -R 6050 $HCE_DIR/

    install_spark
    cp $SPARK_INSTALL/lib/spark-$SPARK_VERSION-yarn-shuffle.jar $HADOOP_PREFIX/share/hadoop/yarn/lib/
    echo "`hostname`: Hadoop installed"
  fi
}

function install_zookeeper() {
  if [ ! -d "$ZOOKEEPER_HOME" ]; then
    get_install $ZOOKEEPER_TARBALL
    cp $CONF_DIR/zoo.cfg $ZOOKEEPER_HOME/conf/
    echo "`hostname`: Zookeeper installed"
  fi
}

function install_fluo() {
  if [ ! -d "$FLUO_HOME" ]; then
    get_install $FLUO_TARBALL
    cp $FLUO_HOME/conf/examples/* $FLUO_HOME/conf/
    cp $CONF_DIR/fluo.properties $FLUO_HOME/conf/
    cp $CONF_DIR/fluo-env.sh $FLUO_HOME/conf/
    echo "`hostname`: Fluo installed"
  fi
}

function install_java() {
  if [ ! -d "$JAVA_INSTALL" ]; then
    get_install $JAVA_TARBALL
    echo "`hostname`: Java installed"
  fi
}

function install_maven() {
  if [ ! -d "$MAVEN_INSTALL" ]; then
    get_install $MAVEN_TARBALL
    ln -s $MAVEN_INSTALL $INSTALL_DIR/maven
    echo "`hostname`: Maven installed"
  fi
}

function install_spark() {
  if [ ! -d "$SPARK_INSTALL" ]; then
    get_install $SPARK_TARBALL
    cp $CONF_DIR/spark-defaults.conf $SPARK_INSTALL/conf
    cp $CONF_DIR/spark-env.sh $SPARK_INSTALL/conf
    echo "`hostname`: Spark installed"
  fi
}

function install_git() {
  if ! rpm -q --quiet git ; then
    sudo yum install -q -y git
    echo "`hostname`: Git installed"
  fi
}

function install_collectd() {
  if ! rpm -q --quiet collectd ; then
    sudo yum install -q -y collectd
    sudo cp $CONF_DIR/collectd.conf /etc/collectd.conf
    sudo service collectd start
    echo "`hostname`: Collectd installed"
  else 
    sudo service collectd stop
    sudo cp $CONF_DIR/collectd.conf /etc/collectd.conf
    sudo service collectd start
  fi
}

function install_metrics(){
  if [ ! -d "$INFLUXDB_INSTALL" ]; then
    get_install $INFLUXDB_TARBALL
    mkdir $INFLUXDB_INSTALL/bin
    mv $INFLUXDB_INSTALL/opt/influxdb/versions/$INFLUXDB_VERSION/* $INFLUXDB_INSTALL/bin
    rm -rf $INFLUXDB_INSTALL/opt
    cp $CONF_DIR/influxdb.conf $INFLUXDB_INSTALL/
    echo "`hostname`: InfluxDB installed"
  fi
  if [ ! -d "$GRAFANA_INSTALL" ]; then
    get_install $GRAFANA_TARBALL
    cp $CONF_DIR/grafana.ini $GRAFANA_INSTALL/conf/custom.ini
    mkdir $GRAFANA_INSTALL/dashboards
    cp $CONF_DIR/grafana/cluster-dashboard.json $GRAFANA_INSTALL/dashboards/
    cp $FLUO_HOME/contrib/grafana/* $GRAFANA_INSTALL/dashboards/
    echo "`hostname`: Grafana installed"
  fi
}

# Exit if any command fails
set -e

rpm -q --quiet epel-release || sudo yum install -q -y epel-release
rpm -q --quiet wget || sudo yum install -q -y wget

# install collectd everywhere if metrics is configured
if [[ "$SETUP_METRICS" = "true" ]]; then
  install_collectd
fi

SERVICES=$@
if [ "$SERVICES" == "--use-config" ]; then
  HOST=`hostname`
  HOSTS_FILE=$CONF_DIR/hosts/hosts_with_services
  SERVICES=`grep -w $HOST $HOSTS_FILE | cut -d ' ' -f 2-`
  if [ -z "$SERVICES" ]; then
    echo "ERROR - The hostname $HOST was not found in $HOSTS_FILE so no services will be installed on this machine"
  fi
fi

for service in $SERVICES; do
  echo "`hostname`: Installing $service service"

  case "$service" in
    accumulomaster)
      install_java
      install_accumulo
      install_hadoop
      install_zookeeper
      ;;
    namenode)
      install_java
      install_hadoop
      ;;
    resourcemanager)
      install_java
      install_hadoop
      ;;
    zookeeper)
      install_java
      install_zookeeper
      ;;
    worker)
      install_java
      install_accumulo
      install_hadoop
      install_zookeeper
      ;;
    fluo)
      install_java
      install_fluo
      ;;
    metrics)
      install_fluo
      install_metrics
      ;;
    dev)
      install_java
      install_git
      install_maven
      install_spark
      ;;
    *)
      echo "Unknown service: $service"
      exit 1
  esac
done
