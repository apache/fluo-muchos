#!/bin/bash

pkill -9 -f fluo.yarn
pkill -9 -f accumulo.start
pkill -9 -f hadoop.hdfs
pkill -9 -f hadoop.yarn
pkill -9 -f QuorumPeerMain
pkill -9 -f org.apache.spark.deploy.history.HistoryServer
sudo pkill -9 -f influxdb
sudo pkill -9 -f grafana-server

exit 0
