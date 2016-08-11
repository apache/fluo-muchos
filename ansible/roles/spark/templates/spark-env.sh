#!/usr/bin/env bash

export SPARK_DIST_CLASSPATH=$({{ hadoop_prefix }}/bin/hadoop classpath)
export HADOOP_CONF_DIR={{ hadoop_prefix }}/etc/hadoop
