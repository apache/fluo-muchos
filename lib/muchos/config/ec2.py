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

import glob
import json
from sys import exit
import os
from .base import SERVICES
from .base import BaseConfig
from .decorators import (
    ansible_play_var,
    default,
)
from ..util import get_ephemeral_devices, get_arch


class Ec2DeployConfig(BaseConfig):
    def __init__(
        self,
        deploy_path,
        config_path,
        hosts_path,
        checksums_path,
        templates_path,
        cluster_name,
    ):
        super(Ec2DeployConfig, self).__init__(
            deploy_path,
            config_path,
            hosts_path,
            checksums_path,
            templates_path,
            cluster_name,
        )
        self.sg_name = cluster_name + "-group"
        self.ephemeral_root = "ephemeral"
        self.cluster_template_d = None
        self.metrics_drive_root = "media-" + self.ephemeral_root
        self.init_template(templates_path)

    def verify_config(self, action):
        self._verify_config(action)

    def verify_launch(self):
        self.verify_instance_type(self.get("ec2", "default_instance_type"))
        self.verify_instance_type(self.get("ec2", "worker_instance_type"))

    def init_nodes(self):
        self.node_d = {}
        for (hostname, value) in self.items("nodes"):
            if hostname in self.node_d:
                exit(
                    "Hostname {0} already exists twice in nodes".format(
                        hostname
                    )
                )
            service_list = []
            for service in value.split(","):
                if service in SERVICES:
                    service_list.append(service)
                else:
                    exit(
                        "Unknown service '{}' declared for node {}".format(
                            service, hostname
                        )
                    )
            self.node_d[hostname] = service_list

    def default_ephemeral_devices(self):
        return get_ephemeral_devices(self.get("ec2", "default_instance_type"))

    def worker_ephemeral_devices(self):
        return get_ephemeral_devices(self.get("ec2", "worker_instance_type"))

    def max_ephemeral(self):
        return max(
            (
                len(self.default_ephemeral_devices()),
                len(self.worker_ephemeral_devices()),
            )
        )

    def node_type_map(self):
        if self.cluster_template_d:
            return self.cluster_template_d["devices"]

        node_types = {}

        node_list = [
            ("default", self.default_ephemeral_devices()),
            ("worker", self.worker_ephemeral_devices()),
        ]

        for (ntype, devices) in node_list:
            node_types[ntype] = {
                "mounts": self.mounts(len(devices)),
                "devices": devices,
            }

        return node_types

    def mount_root(self):
        return "/media/" + self.ephemeral_root

    @ansible_play_var
    @default("ext3")
    def fstype(self):
        return self.get("ec2", "fstype")

    @ansible_play_var
    @default("no")
    def force_format(self):
        return self.get("ec2", "force_format")

    def data_dirs_common(self, nodeType):
        return self.node_type_map()[nodeType]["mounts"]

    def metrics_drive_ids(self):
        drive_ids = []
        for i in range(0, self.max_ephemeral()):
            drive_ids.append(self.metrics_drive_root + str(i))
        return drive_ids

    def shutdown_delay_minutes(self):
        return self.get("ec2", "shutdown_delay_minutes")

    def verify_instance_type(self, instance_type):
        if not self.cluster_template_d:
            if get_arch(instance_type) == "pvm":
                exit(
                    "ERROR - Configuration contains instance type '{0}' "
                    "that uses pvm architecture."
                    "Only hvm architecture is supported!".format(instance_type)
                )

    def instance_tags(self):
        retd = {}
        if self.has_option("ec2", "instance_tags"):
            value = self.get("ec2", "instance_tags")
            if value:
                for kv in value.split(","):
                    (key, val) = kv.split(":")
                    retd[key] = val
        return retd

    def init_template(self, templates_path):
        if self.has_option("ec2", "cluster_template"):
            template_id = self.get("ec2", "cluster_template")
            template_path = os.path.join(templates_path, template_id)
            if os.path.exists(template_path):
                self.cluster_template_d = {"id": template_id}
                self.load_template_ec2_requests(template_path)
                self.load_template_device_map(template_path)
            self.validate_template()

    def load_template_ec2_requests(self, template_dir):
        for json_path in glob.glob(os.path.join(template_dir, "*.json")):
            service = os.path.basename(json_path).rsplit(".", 1)[0]
            if service not in SERVICES:
                exit(
                    "ERROR - Template '{0}' has unrecognized option '{1}'. "
                    "Must be one of {2}".format(
                        self.cluster_template_d["id"], service, str(SERVICES)
                    )
                )
            with open(json_path, "r") as json_file:
                # load as string, so we can use string.Template
                # to inject config values
                self.cluster_template_d[service] = json_file.read()

    def load_template_device_map(self, template_dir):
        device_map_path = os.path.join(template_dir, "devices")
        if not os.path.isfile(device_map_path):
            exit(
                "ERROR - template '{0}' is missing 'devices' config".format(
                    self.cluster_template_d["id"]
                )
            )
        with open(device_map_path, "r") as json_file:
            self.cluster_template_d["devices"] = json.load(json_file)

    def validate_template(self):
        if not self.cluster_template_d:
            exit(
                "ERROR - Template '{0}' is not defined!".format(
                    self.get("ec2", "cluster_template")
                )
            )

        if "worker" not in self.cluster_template_d:
            exit(
                "ERROR - '{0}' template config is invalid. No 'worker' "
                "launch request is defined".format(
                    self.cluster_template_d["id"]
                )
            )

        if "worker" not in self.cluster_template_d["devices"]:
            exit(
                "ERROR - '{0}' template is invalid. The devices file must "
                "have a 'worker' device map".format(
                    self.cluster_template_d["id"]
                )
            )

        if "default" not in self.cluster_template_d["devices"]:
            exit(
                "ERROR - '{0}' template is invalid. The devices file must "
                "have a 'default' device map".format(
                    self.cluster_template_d["id"]
                )
            )

        # Validate the selected launch template for each host

        worker_count = 0
        for hostname in self.node_d:
            # first service listed denotes the selected template
            selected_ec2_request = self.node_d[hostname][0]
            if "worker" == selected_ec2_request:
                worker_count = worker_count + 1
            else:
                if "worker" in self.node_d[hostname]:
                    exit(
                        "ERROR - '{0}' node config is invalid. The 'worker'"
                        " service should be listed first".format(hostname)
                    )
            if selected_ec2_request not in self.cluster_template_d:
                if len(self.node_d[hostname]) > 1:
                    print(
                        "Hint: In template mode, the first service listed"
                        " for a host denotes its EC2 template"
                    )
                exit(
                    "ERROR - '{0}' node config is invalid. No EC2 "
                    "template defined for the '{1}' service".format(
                        hostname, selected_ec2_request
                    )
                )

        if worker_count == 0:
            exit(
                "ERROR - No worker instances are defined "
                "for template '{0}'".format(self.cluster_template_d["id"])
            )
