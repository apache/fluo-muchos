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

SSH_OPTS=(-tt -o 'StrictHostKeyChecking no' -A)

function verify_checksum() {
  tarball=$1
  expected_md5=$2
  actual_md5=`md5sum $TARBALLS_DIR/$tarball | awk '{print $1}'`

  if [[ "$actual_md5" != "$expected_md5" ]]; then
    echo "The MD5 checksum ($actual_md5) of $tarball does not match the expected checksum ($expected_md5)"
    exit 1
  fi
}

echo "Started cluster setup"

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

  echo "Configuring system settings on all nodes"
  IMPL_DIR=$BIN_DIR/impl
  pssh -p 10 -x "-tt" -i -t 300 -h $CONF_DIR/hosts/all_ips "$IMPL_DIR/configure-system.sh"
  source $HOME/.bashrc

  echo "Configuring hostname and drives on all nodes"
  pssh -p 10 -x "-tt" -i -t 300 -h $CONF_DIR/hosts/all_ips "$IMPL_DIR/configure-drives.sh"
else
  echo "User chose to skip configuring machines"
fi

echo "Downloading required software"
wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/zookeeper/zookeeper-$ZOOKEEPER_VERSION/$ZOOKEEPER_TARBALL &
wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/hadoop/common/hadoop-$HADOOP_VERSION/$HADOOP_TARBALL &
wget -nc -nv -P $TARBALLS_DIR --no-check-certificate --no-cookies --header "Cookie: oraclelicense=accept-securebackup-cookie" http://download.oracle.com/otn-pub/java/jdk/8u60-b27/$JAVA_TARBALL &
wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/maven/maven-3/$MAVEN_VERSION/binaries/$MAVEN_TARBALL &
wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/spark/spark-$SPARK_VERSION/$SPARK_TARBALL &
if [[ "$DOWNLOAD_FLUO" = "true" ]]; then
  if [[ "$FLUO_VERSION" =~ "SNAPSHOT" ]]; then
    SONATYPE_URL=https://oss.sonatype.org/content/repositories/snapshots/io/fluo/fluo-distribution/$FLUO_VERSION/
    FLUO_TARBALL_URL=`curl -s $SONATYPE_URL | grep 'bin.tar.gz"' | tail -1 | cut -d'"' -f 2`
    FLUO_MD5_URL=`curl -s $SONATYPE_URL | grep 'bin.tar.gz.md5"' | tail -1 | cut -d'"' -f 2`
  else
    SONATYPE_URL=https://repo1.maven.org/maven2/io/fluo/fluo-distribution/$FLUO_VERSION
    FLUO_TARBALL_URL=$SONATYPE_URL/fluo-distribution-$FLUO_VERSION-bin.tar.gz
    FLUO_MD5_URL=$SONATYPE_URL/fluo-distribution-$FLUO_VERSION-bin.tar.gz.md5
  fi
  wget -nc -nv -O $TARBALLS_DIR/$FLUO_TARBALL $FLUO_TARBALL_URL &
  wget -nc -nv -O $TARBALLS_DIR/$FLUO_TARBALL.md5 $FLUO_MD5_URL &
fi
if [[ $ACCUMULO_VERSION != *"SNAPSHOT"* ]]; then
  wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/accumulo/$ACCUMULO_VERSION/$ACCUMULO_TARBALL &
fi
if [[ "$SETUP_METRICS" = "true" ]]; then
  wget -nc -nv -P $TARBALLS_DIR https://s3.amazonaws.com/influxdb/$INFLUXDB_TARBALL &
  wget -nc -nv -P $TARBALLS_DIR https://grafanarel.s3.amazonaws.com/builds/$GRAFANA_TARBALL &
fi

echo "Waiting for downloads to finish"
wait
echo "Downloads have finished!"

echo "Verifying checksums of software"
verify_checksum $HADOOP_TARBALL $HADOOP_MD5
verify_checksum $JAVA_TARBALL b8ca513d4f439782c019cb78cd7fd101
verify_checksum $ZOOKEEPER_TARBALL $ZOOKEEPER_MD5
verify_checksum $MAVEN_TARBALL $MAVEN_MD5
verify_checksum $SPARK_TARBALL $SPARK_MD5
if [[ "$DOWNLOAD_FLUO" = "true" ]]; then
  verify_checksum $FLUO_TARBALL `cat $TARBALLS_DIR/$FLUO_TARBALL.md5`
fi
if [[ $ACCUMULO_VERSION != *"SNAPSHOT"* ]]; then
  verify_checksum $ACCUMULO_TARBALL $ACCUMULO_MD5
fi
if [[ "$SETUP_METRICS" = "true" ]]; then
  verify_checksum $INFLUXDB_TARBALL $INFLUXDB_MD5
  verify_checksum $GRAFANA_TARBALL $GRAFANA_MD5
fi
echo "Checksums are valid"

echo "Confirming that nothing running on cluster"
$BIN_DIR/fluo-cluster kill &> /dev/null

echo "Removing any previous data"
pssh -i -h $CONF_DIR/hosts/all_hosts "rm -rf /media/ephemeral*/zoo*  /media/ephemeral*/hadoop* /media/ephemeral*/yarn* /media/ephemeral*/influxdb /media/ephemeral*/grafana"

echo "Installing all services on cluster"
pssh -p 10 -x "-tt -o 'StrictHostKeyChecking no'" -t 300 -i -h $CONF_DIR/hosts/all_hosts "$BIN_DIR/impl/install.sh"
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

echo -e "\nCluster setup is finished"
