#!/bin/bash
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


pkill -9 -f fluo.yarn
pkill -9 -f accumulo.start
pkill -9 -f hadoop.hdfs
pkill -9 -f hadoop.yarn
pkill -9 -f QuorumPeerMain
pkill -9 -f JobHistoryServer
pkill -9 -f org.apache.spark.deploy.history.HistoryServer
sudo pkill -9 -f influxdb
sudo pkill -9 -f grafana-server

exit 0
