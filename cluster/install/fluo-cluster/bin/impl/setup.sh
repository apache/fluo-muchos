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

function verify_checksum() {
  tarball=$1
  expected_md5=$2
  actual_md5=`md5sum $TARBALLS_DIR/$tarball | awk '{print $1}'`

  if [[ "$actual_md5" != "$expected_md5" ]]; then
    echo "The MD5 checksum ($actual_md5) of $tarball does not match the expected checksum ($expected_md5)"
    exit 1
  fi
}

echo "Downloading required software"
wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/zookeeper/zookeeper-$ZOOKEEPER_VERSION/$ZOOKEEPER_TARBALL &
wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/hadoop/common/hadoop-$HADOOP_VERSION/$HADOOP_TARBALL &
wget -nc -nv -P $TARBALLS_DIR --no-check-certificate --no-cookies --header "Cookie: oraclelicense=accept-securebackup-cookie" http://download.oracle.com/otn-pub/java/jdk/8u60-b27/$JAVA_TARBALL &
wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/maven/maven-3/$MAVEN_VERSION/binaries/$MAVEN_TARBALL &
wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/spark/spark-$SPARK_VERSION/$SPARK_TARBALL &
echo "Waiting"
wait

echo "Verifying checksums of software"
verify_checksum $HADOOP_TARBALL $HADOOP_MD5
verify_checksum $JAVA_TARBALL b8ca513d4f439782c019cb78cd7fd101
verify_checksum $ZOOKEEPER_TARBALL $ZOOKEEPER_MD5
verify_checksum $MAVEN_TARBALL $MAVEN_MD5
verify_checksum $SPARK_TARBALL $SPARK_MD5

if [[ $ACCUMULO_VERSION != *"SNAPSHOT"* ]]
then
  wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/accumulo/$ACCUMULO_VERSION/$ACCUMULO_TARBALL
  verify_checksum $ACCUMULO_TARBALL $ACCUMULO_MD5
fi

# do an initial ssh to each node to set-up the strict keys
for host in `cat $CONF_DIR/hosts/all_except_proxy`; do
   ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$host mkdir -p $TARBALLS_DIR
done

sudo yum install -y pssh

echo "Copying scripts to all nodes"
pscp.pssh -h $CONF_DIR/hosts/all_except_proxy $TARBALLS_DIR/install.tar.gz $TARBALLS_DIR/install.tar.gz
pssh -i -h $CONF_DIR/hosts/all_except_proxy "rm -rf $INSTALL_DIR; tar -C $BASE_DIR -xzf $TARBALLS_DIR/install.tar.gz"

echo "Confirm that nothing is running on cluster"
$BIN_DIR/fluo-cluster kill &> /dev/null

$BIN_DIR/fluo-cluster configure
