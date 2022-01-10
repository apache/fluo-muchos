#! /usr/bin/env bash
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

export ACCUMULO_LOG_DIR={{ worker_data_dirs[0] }}/logs/accumulo
export ZOOKEEPER_HOME={{ zookeeper_home }}
export JAVA_HOME={{ java_home }}

{% if accumulo_major_version == '1' %}

export HADOOP_PREFIX={{ hadoop_home }}
export HADOOP_CONF_DIR="$HADOOP_PREFIX/etc/hadoop"
export ACCUMULO_TSERVER_OPTS="-Xmx{{ accumulo_tserv_mem }} -Xms{{ accumulo_tserv_mem }}"
export ACCUMULO_MASTER_OPTS="-Xmx256m -Xms256m"
export ACCUMULO_MONITOR_OPTS="-Xmx128m -Xms64m"
export ACCUMULO_GC_OPTS="-Xmx128m -Xms128m"
export ACCUMULO_SHELL_OPTS="-Xmx256m -Xms64m"
export ACCUMULO_GENERAL_OPTS="-XX:+UseConcMarkSweepGC -XX:CMSInitiatingOccupancyFraction=75 -Djava.net.preferIPv4Stack=true -XX:+CMSClassUnloadingEnabled"
export ACCUMULO_OTHER_OPTS="-Xmx256m -Xms64m"
export ACCUMULO_KILL_CMD='kill -9 %p'
export NUM_TSERVERS=1
export MALLOC_ARENA_MAX=${MALLOC_ARENA_MAX:-1}
{% if cluster_type == 'azure' and az_use_app_insights %}
# Activate the Application Insights agent
export ACCUMULO_TSERVER_OPTS="$ACCUMULO_TSERVER_OPTS -javaagent:{{ az_app_insights_home }}/appinsights-agent.jar"
export ACCUMULO_MASTER_OPTS="$ACCUMULO_MASTER_OPTS -javaagent:{{ az_app_insights_home }}/appinsights-agent.jar"
export ACCUMULO_GC_OPTS="$ACCUMULO_GC_OPTS -javaagent:{{ az_app_insights_home }}/appinsights-agent.jar"
{% endif %}

{% else %}

export HADOOP_HOME={{ hadoop_home }}
export HADOOP_CONF_DIR="$HADOOP_HOME/etc/hadoop"

add_jar_prefix_to_classpath() {
  for JAR in "$1"*jar; do
    CLASSPATH="${CLASSPATH}:${JAR}"
  done
}
## Build using existing CLASSPATH, conf/ directory, dependencies in lib/, and external Hadoop & Zookeeper dependencies
if [[ -n "$CLASSPATH" ]]; then
  CLASSPATH="${CLASSPATH}:${conf}"
else
  CLASSPATH="${conf}"
fi
CLASSPATH="${CLASSPATH}:${lib}/*:${HADOOP_CONF_DIR}:${ZOOKEEPER_HOME}/*"
add_jar_prefix_to_classpath "${ZOOKEEPER_HOME}/lib/zookeeper-"
CLASSPATH="${CLASSPATH}:${HADOOP_HOME}/share/hadoop/client/*"
{% if cluster_type == 'azure' and use_adlsg2 %}
add_jar_prefix_to_classpath "${HADOOP_HOME}/share/hadoop/tools/lib/azure-data-lake-store-sdk-"
add_jar_prefix_to_classpath "${HADOOP_HOME}/share/hadoop/tools/lib/azure-keyvault-core-"
add_jar_prefix_to_classpath "${HADOOP_HOME}/share/hadoop/tools/lib/hadoop-azure-"
add_jar_prefix_to_classpath "${HADOOP_HOME}/share/hadoop/tools/lib/azure-storage-"
add_jar_prefix_to_classpath "${HADOOP_HOME}/share/hadoop/tools/lib/wildfly-openssl-"
add_jar_prefix_to_classpath "${HADOOP_HOME}/share/hadoop/common/lib/jaxb-api-"
add_jar_prefix_to_classpath "${HADOOP_HOME}/share/hadoop/common/lib/jaxb-impl-"
add_jar_prefix_to_classpath "${HADOOP_HOME}/share/hadoop/common/lib/commons-lang3-"
add_jar_prefix_to_classpath "${HADOOP_HOME}/share/hadoop/common/lib/httpclient-"
add_jar_prefix_to_classpath "${HADOOP_HOME}/share/hadoop/common/lib/jackson-core-asl-"
add_jar_prefix_to_classpath "${HADOOP_HOME}/share/hadoop/common/lib/jackson-mapper-asl-"
{% if not use_hdfs|default(True) %}
add_jar_prefix_to_classpath "${HADOOP_HOME}/share/hadoop/hdfs/lib/jetty-util-ajax-"
{% endif %}
{% endif %}
export CLASSPATH

JAVA_OPTS=("${ACCUMULO_JAVA_OPTS[@]}"
  '-XX:+UseConcMarkSweepGC'
  '-XX:CMSInitiatingOccupancyFraction=75'
  '-XX:+CMSClassUnloadingEnabled'
  '-XX:OnOutOfMemoryError=kill -9 %p'
  '-XX:-OmitStackTraceInFastThrow'
  '-Djava.net.preferIPv4Stack=true'
{% if cluster_type == 'azure' and use_adlsg2 %}
  '-Dorg.wildfly.openssl.path=/usr/lib64'
{% endif %}
  "-Daccumulo.native.lib.path=${lib}/native")

case "$cmd" in
  {{ master_manager }})  JAVA_OPTS=("${JAVA_OPTS[@]}" '-Xmx512m' '-Xms512m') ;;
  monitor) JAVA_OPTS=("${JAVA_OPTS[@]}" '-Xmx256m' '-Xms256m') ;;
  gc)      JAVA_OPTS=("${JAVA_OPTS[@]}" '-Xmx256m' '-Xms256m') ;;
  tserver) JAVA_OPTS=("${JAVA_OPTS[@]}" '-Xmx{{ accumulo_tserv_mem }}' '-Xms{{ accumulo_tserv_mem }}') ;;
  *)       JAVA_OPTS=("${JAVA_OPTS[@]}" '-Xmx256m' '-Xms64m') ;;
esac



JAVA_OPTS=("${JAVA_OPTS[@]}"
  "-Daccumulo.log.dir=${ACCUMULO_LOG_DIR}"
  "-Daccumulo.application=${cmd}${ACCUMULO_SERVICE_INSTANCE}_$(hostname)"
{% if accumulo_version is version('2.1.0','>=') %}
   "-Daccumulo.metrics.service.instance=${ACCUMULO_SERVICE_INSTANCE}"
   "-Dlog4j2.contextSelector=org.apache.logging.log4j.core.async.AsyncLoggerContextSelector"
{% endif %}
)

case "$cmd" in
{% if accumulo_version is version('2.1.0','>=') %}
  monitor|gc|manager|tserver|compaction-coordinator|compactor)
    JAVA_OPTS=("${JAVA_OPTS[@]}" "-Dlog4j.configurationFile=log4j2-service.properties")
    ;;
{% else %}
  monitor)
    JAVA_OPTS=("${JAVA_OPTS[@]}" "-Dlog4j.configuration=log4j-monitor.properties")
    ;;
  gc|master|tserver|tracer)
    JAVA_OPTS=("${JAVA_OPTS[@]}" "-Dlog4j.configuration=log4j-service.properties")
    ;;
{% endif %}
  *)
    # let log4j use its default behavior (log4j.xml, log4j.properties)
    true
    ;;
esac
{% if cluster_type == 'azure' and az_use_app_insights %}

# Enable the application insights agent for tablet servers, manager, and gc processes
case "$cmd" in
  tserver|master|manager|gc)
    JAVA_OPTS=("${JAVA_OPTS[@]}" '-javaagent:{{ az_app_insights_home }}/appinsights-agent.jar')
    ;;
  *)
    true
    ;;
esac
{% endif %}
export JAVA_OPTS

export MALLOC_ARENA_MAX=${MALLOC_ARENA_MAX:-1}
export LD_LIBRARY_PATH="${HADOOP_HOME}/lib/native:${LD_LIBRARY_PATH}"
{% endif %}
