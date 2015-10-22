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

function verify_checksum() {
  tarball=$1
  expected_md5=$2
  actual_md5=`md5sum $TARBALLS_DIR/$tarball | awk '{print $1}'`

  if [[ "$actual_md5" != "$expected_md5" ]]; then
    echo "The MD5 checksum ($actual_md5) of $tarball does not match the expected checksum ($expected_md5)"
    exit 1
  fi
}

# Exit if any command fails
set -e

echo "Cluster setup started"

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
echo "Checksums are valid"

echo "Installing pssh"
sudo yum install -q -y pssh

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
  pscp.pssh -h $CONF_DIR/hosts/all_except_proxy $SSH_DIR/id_rsa $SSH_DIR/id_rsa.pub

  echo "Configuring non-proxy nodes"
  pssh -x "-tt -o 'StrictHostKeyChecking no'" -i -h $CONF_DIR/hosts/all_except_proxy "$BIN_DIR/fluo-cluster configure --use-config"

  echo "Configuring proxy"
  $BIN_DIR/fluo-cluster configure --use-config
else
  echo "User chose not to configure ~/.ssh/config, /etc/hosts, & ~/.bashrc on cluster"
fi

echo "Cluster setup finished"
