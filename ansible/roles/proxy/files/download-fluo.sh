#!/bin/bash

TARBALLS_DIR=$1
FLUO_TARBALL=$2
FLUO_VERSION=$3

if [[ "$FLUO_VERSION" =~ "SNAPSHOT" ]]; then
  SONATYPE_URL=https://oss.sonatype.org/content/repositories/snapshots/io/fluo/fluo-distribution/$FLUO_VERSION/
  FLUO_TARBALL_URL=`curl -s $SONATYPE_URL | grep 'bin.tar.gz"' | tail -1 | cut -d'"' -f 2`
  FLUO_MD5_URL=`curl -s $SONATYPE_URL | grep 'bin.tar.gz.md5"' | tail -1 | cut -d'"' -f 2`
else
  SONATYPE_URL=https://repo1.maven.org/maven2/io/fluo/fluo-distribution/$FLUO_VERSION
  FLUO_TARBALL_URL=$SONATYPE_URL/fluo-distribution-$FLUO_VERSION-bin.tar.gz
  FLUO_MD5_URL=$SONATYPE_URL/fluo-distribution-$FLUO_VERSION-bin.tar.gz.md5
fi
wget -nc -nv -O $TARBALLS_DIR/$FLUO_TARBALL $FLUO_TARBALL_URL
wget -nc -nv -O $TARBALLS_DIR/$FLUO_TARBALL.md5 $FLUO_MD5_URL

EXPECTED_SUM=`cat $TARBALLS_DIR/$FLUO_TARBALL.md5`
ACTUAL_SUM=`md5sum $TARBALLS_DIR/$FLUO_TARBALL | awk '{print $1}'`
if [[ "$ACTUAL_SUM" != "$EXPECTED_SUM" ]]; then
  echo "The md5 checksum ($ACTUAL_SUM) of $FLUO_TARBALL does not match the expected checksum ($EXPECTED_SUM)"
  exit 1
fi
