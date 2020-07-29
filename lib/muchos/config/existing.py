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

from .base import BaseConfig


class ExistingDeployConfig(BaseConfig):
    def __init__(
        self,
        deploy_path,
        config_path,
        hosts_path,
        checksums_path,
        templates_path,
        cluster_name,
    ):
        super(ExistingDeployConfig, self).__init__(
            deploy_path,
            config_path,
            hosts_path,
            checksums_path,
            templates_path,
            cluster_name,
        )

    def verify_config(self, action):
        self._verify_config(action)

    def verify_launch(self):
        pass

    def node_type_map(self):
        node_types = {}
        return node_types

    def mount_root(self):
        return self.get("existing", "mount_root")

    def data_dirs_common(self, nodeType):
        return self.get("existing", "data_dirs").split(",")

    def metrics_drive_ids(self):
        return self.get("existing", "metrics_drive_ids").split(",")
