#!/usr/bin/env bash

export SPARK_DIST_CLASSPATH=$({{ hadoop_home }}/bin/hadoop classpath)
export HADOOP_CONF_DIR={{ hadoop_home }}/etc/hadoop
