#!/bin/bash

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

SSH_OPTS=(-o 'StrictHostKeyChecking no' -A)

if [ "$CONFIGURE_CLUSTER" == "true" ]; then
  if [ ! -f /home/$CLUSTER_USERNAME/.ssh/id_rsa ]; then
   ssh-keygen  -q -t rsa -N ''  -f /home/$CLUSTER_USERNAME/.ssh/id_rsa
  fi
  while read line; do
    IFS=' ' read -ra ARR <<< "$line"
    ADDR=${ARR[0]}
    HOST=${ARR[1]}
    NUM_EPHEMERAL=${ARR[2]}
    ssh -tt "${SSH_OPTS[@]}" $CLUSTER_USERNAME@$ADDR $BIN_DIR/fluo-cluster configure-local $HOST $NUM_EPHEMERAL < /dev/null
  done < $CONF_DIR/hosts/all_for_configure
else
  echo "User chose not to configure ~/.ssh/config, /etc/hosts, & ~/.bashrc on cluster"
fi
