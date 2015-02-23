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

export HADOOP_PREFIX=$HADOOP_PREFIX
export HADOOP_CONF_DIR="$HADOOP_PREFIX/etc/hadoop"
export ZOOKEEPER_HOME=$ZOOKEEPER_HOME
export ACCUMULO_LOG_DIR=$$ACCUMULO_HOME/logs
if [ -f $${ACCUMULO_CONF_DIR}/accumulo.policy ]
then
   POLICY="-Djava.security.manager -Djava.security.policy=$${ACCUMULO_CONF_DIR}/accumulo.policy"
fi
export ACCUMULO_TSERVER_OPTS="$${POLICY} -Xmx768m -Xms768m "
export ACCUMULO_MASTER_OPTS="$${POLICY} -Xmx256m -Xms256m"
export ACCUMULO_MONITOR_OPTS="$${POLICY} -Xmx128m -Xms64m"
export ACCUMULO_GC_OPTS="-Xmx128m -Xms128m"
export ACCUMULO_GENERAL_OPTS="-XX:+UseConcMarkSweepGC -XX:CMSInitiatingOccupancyFraction=75 -Djava.net.preferIPv4Stack=true"
export ACCUMULO_OTHER_OPTS="-Xmx256m -Xms64m"
# what do when the JVM runs out of heap memory
export ACCUMULO_KILL_CMD='kill -9 %p'
