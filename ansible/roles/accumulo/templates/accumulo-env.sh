#! /usr/bin/env bash

# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

export ACCUMULO_TSERVER_OPTS="-Xmx{{ accumulo_tserv_mem }} -Xms{{ accumulo_tserv_mem }}"
export ACCUMULO_MASTER_OPTS="-Xmx256m -Xms256m"
export ACCUMULO_MONITOR_OPTS="-Xmx128m -Xms64m"
export ACCUMULO_GC_OPTS="-Xmx128m -Xms128m"
export ACCUMULO_SHELL_OPTS="-Xmx256m -Xms64m"
export ACCUMULO_GENERAL_OPTS="-XX:+UseConcMarkSweepGC -XX:CMSInitiatingOccupancyFraction=75 -Djava.net.preferIPv4Stack=true -XX:+CMSClassUnloadingEnabled"
export ACCUMULO_OTHER_OPTS="-Xmx256m -Xms64m"

export JAVA_HOME={{ java_home }}
export HADOOP_PREFIX={{ hadoop_prefix }}
export HADOOP_CONF_DIR="$HADOOP_PREFIX/etc/hadoop"
export ZOOKEEPER_HOME={{ zookeeper_home }}

{% if accumulo_major_version == '1' %}
export ACCUMULO_LOG_DIR=$ACCUMULO_HOME/logs
# what do when the JVM runs out of heap memory
export ACCUMULO_KILL_CMD='kill -9 %p'
#needed for Accumulo 1.8
export NUM_TSERVERS=1
{% endif %}
