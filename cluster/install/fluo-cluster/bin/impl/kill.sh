#!/usr/bin/env bash

# Copyright 2014 Fluo authors (see AUTHORS)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific 

SSH_OPTS=(-tt -o 'StrictHostKeyChecking no' -A)

echo "Killing cluster"
for host in `cat $CONF_DIR/hosts/all_ips`; do
  ssh "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$host $BIN_DIR/impl/kill-local.sh
done
