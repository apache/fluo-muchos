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

from muchos.config import BaseConfig
from muchos.config.decorators import *
from muchos.config.validators import *
from sys import exit
from muchos.util import get_ephemeral_devices, get_arch
import os
import json
import glob


class AzureDeployConfig(BaseConfig):

    def __init__(self, deploy_path, config_path, hosts_path, checksums_path, templates_path, cluster_name):
        super(AzureDeployConfig, self).__init__(deploy_path, config_path, hosts_path, checksums_path, templates_path, cluster_name)

    def verify_config(self, action):
        self._verify_config(action)

        proxy = self.get('general', 'proxy_hostname')
        cluster_type = self.get('general', 'cluster_type')
        if cluster_type not in ['azure']:
            if not proxy:
                exit("ERROR - proxy.hostname must be set in muchos.props")

            if proxy not in self.node_d:
                exit("ERROR - The proxy (set by property proxy_hostname={0}) cannot be found in 'nodes' section of "
                     "muchos.props".format(proxy))

    def verify_launch(self):
        pass

    def node_type_map(self):
        node_types = {}

    def mount_root(self):
        return self.get('azure', 'mount_root')

    def fstype(self):
        retval = None
        return retval

    def force_format(self):
        retval = 'no'
        return retval

    def data_dirs_common(self, nodeType):
        data_dirs = []

        num_disks = int(self.get("azure", "numdisks"))
        range_var = num_disks + 1
        for diskNum in range(1, range_var):
            data_dirs.append(self.get("azure", "mount_root") +
                                str(diskNum))

        return data_dirs

    def metrics_drive_ids(self):
        drive_ids = []
        range_var = int(self.get("azure", "numdisks")) + 1
        for i in range(1, range_var):
            drive_ids.append(self.get("azure", "metrics_drive_root") +
                                str(i))
        return drive_ids

    def shutdown_delay_minutes(self):
        retval = '0'
        return retval

    def instance_tags(self):
        return {}


AZURE_VAR_DEFAULTS = {
  'azure_fileshare_mount': None,
  'azure_fileshare': None,
  'azure_fileshare_username': None,
  'azure_fileshare_password': None,
  'az_omsIntegrationNeeded': None,
  'az_logs_id': None,
  'az_logs_key': None
}
