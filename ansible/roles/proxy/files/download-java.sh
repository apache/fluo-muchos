#!/bin/bash

TARBALLS_DIR=$1
JAVA_TARBALL=$2
EXPECTED_SUM=$3

wget -nc -nv -P $TARBALLS_DIR --no-check-certificate --no-cookies --header "Cookie: oraclelicense=accept-securebackup-cookie" http://download.oracle.com/otn-pub/java/jdk/8u60-b27/$JAVA_TARBALL

ACTUAL_SUM=`sha256sum $TARBALLS_DIR/$JAVA_TARBALL | awk '{print $1}'`
if [[ "$ACTUAL_SUM" != "$EXPECTED_SUM" ]]; then
  echo "The SHA256 checksum ($ACTUAL_SUM) of $JAVA_TARBALL does not match the expected checksum ($EXPECTED_SUM)"
  exit 1
fi
