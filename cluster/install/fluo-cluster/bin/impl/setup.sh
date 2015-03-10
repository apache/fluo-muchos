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

# Download required tarballs
wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/zookeeper/zookeeper-$ZOOKEEPER_VERSION/$ZOOKEEPER_TARBALL
verify_checksum $ZOOKEEPER_TARBALL $ZOOKEEPER_MD5

if [[ $ACCUMULO_VERSION != *"SNAPSHOT"* ]]
then
  wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/accumulo/$ACCUMULO_VERSION/$ACCUMULO_TARBALL
  verify_checksum $ACCUMULO_TARBALL $ACCUMULO_MD5
fi

wget -nc -nv -P $TARBALLS_DIR $APACHE_MIRROR/hadoop/common/hadoop-$HADOOP_VERSION/$HADOOP_TARBALL
verify_checksum $HADOOP_TARBALL $HADOOP_MD5

JAVA_TARBALL=jdk-7u75-linux-x64.tar.gz
wget -nc -nv -P $TARBALLS_DIR --no-check-certificate --no-cookies --header "Cookie: oraclelicense=accept-securebackup-cookie" http://download.oracle.com/otn-pub/java/jdk/7u75-b13/$JAVA_TARBALL
verify_checksum $JAVA_TARBALL 6f1f81030a34f7a9c987f8b68a24d139

# Push install directory to all hosts
for host in `cat $CONF_DIR/hosts/all_except_proxy`; do
  echo "`hostname`: Copying scripts to $host"
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$host mkdir -p $TARBALLS_DIR
  scp $TARBALLS_DIR/install.tar.gz $CLUSTER_USERNAME@$host:$TARBALLS_DIR
  ssh $CLUSTER_USERNAME@$host "rm -rf $INSTALL_DIR; tar -C $BASE_DIR -xzf $TARBALLS_DIR/install.tar.gz"
done

$BIN_DIR/fluo-cluster kill &> /dev/null

$BIN_DIR/fluo-cluster configure
