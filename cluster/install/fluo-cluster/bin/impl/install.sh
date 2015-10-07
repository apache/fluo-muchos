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
    sudo cp $CONF_DIR/hadoop/container-executor.cfg $HCE_DIR/etc/hadoop/
    sudo chown -R root:ec2-user $HCE_DIR/
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
    cp $CONF_DIR/metrics.yaml $FLUO_HOME/conf/
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
    echo "`hostname`: Spark installed"
  fi
}

function install_git() {
  if ! rpm -q --quiet git ; then
    sudo yum install -q -y git
    echo "`hostname`: Git installed"
  fi
}

function install_graphite(){
  if ! rpm -qa | grep -qw docker; then  
    sudo yum install -y docker
    sudo mv /var/lib/docker "$DATA_DIR/"
    sudo ln -s "$DATA_DIR/docker" /var/lib/
    sudo service docker start

    sudo docker run -d --name graphite -p 80:80 -p 2003:2003 -p 8125:8125/udp hopsoft/graphite-statsd

    sudo yum install -y expect
    expect << DONE
spawn sudo docker exec -t -i graphite python /opt/graphite/webapp/graphite/manage.py changepassword
expect "Password: "
send -- "foo10\r"
expect "Password (again): "
send -- "foo10\r"
expect eof
DONE

  else
    RUNNING=$(sudo docker inspect --format="{{ .State.Running }}" graphite 2> /dev/null)
    if [ $? -eq 1 ]; then
      #UNKNOWN container
      sudo docker run -d --name graphite -p 80:80 -p 2003:2003 -p 8125:8125/udp hopsoft/graphite-statsd
    fi

    if [ "$RUNNING" == "false" ]; then
      sudo docker start graphite
    fi 
  fi

  #setup initial dashboard for fluo
  # based on comment from http://serverfault.com/questions/505871/graphite-edit-dashboard  which did not mention --data-urlencode state@
  while ! curl --data-urlencode state@$CONF_DIR/graphite-dash.json http://localhost:80/dashboard/save/fluo
  do
    echo "Unable to update graphite dashboard... sleeping and retrying"    
    sleep 1
  done
}

# Exit if any command fails
set -e

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
    graphite)
      install_graphite
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
