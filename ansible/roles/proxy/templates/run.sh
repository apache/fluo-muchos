#!/usr/bin/env bash

APPS_DIR={{ cluster_basedir }}/apps
export HADOOP_PREFIX={{ hadoop_prefix }}
export HADOOP_CONF_DIR={{ hadoop_prefix }}/etc/hadoop
export ACCUMULO_HOME={{ accumulo_home }}
export FLUO_HOME={{ fluo_home }}
export ZOOKEEPER_HOME={{ zookeeper_home }}
export SPARK_HOME={{ spark_home }}

if [ "$#" -lt 4 ]; then
  echo "Usage: run.sh <app_name> <repo> <branch> <command> [args...]"
  exit 1
fi

export FLUO_APP_NAME=$1
APP_REPO=$2
APP_BRANCH=$3
APP_COMMAND=$4

mkdir -p $APPS_DIR
cd $APPS_DIR

rm -rf $FLUO_APP_NAME
git clone -b $APP_BRANCH $APP_REPO $FLUO_APP_NAME

cd $FLUO_APP_NAME

$APP_COMMAND ${@:5}
