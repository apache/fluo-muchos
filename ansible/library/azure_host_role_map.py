#!/usr/bin/python3
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

from ansible.module_utils.basic import AnsibleModule
from collections import defaultdict
import os
from os.path import join

deploy_path = os.environ.get("MUCHOS_HOME")


def label(hosts, labels):
    hld = defaultdict(list)
    for i, host in enumerate(hosts):
        for tmpLabel, n in labels.items():
            if i < n:
                hld[host].append(tmpLabel)
    return hld


def stringify(L, hns):
    # Flatten the list of dicts
    labels = {k: v for d in L for k, v in d.items()}
    label_string_dict = {k: ",".join(v) for k, v in labels.items()}
    label_list = [
        "{} = {} {}".format(k, v, hns[k]) for k, v in label_string_dict.items()
    ]
    return "\n".join(label_list)


def main():

    fields = {
        "hosts": {"required": True, "type": "list"},
        "vars_list": {"required": True, "type": "dict"},
        "cluster_name": {"required": True, "type": "str"},
    }

    module = AnsibleModule(argument_spec=fields)
    vars_list = module.params["vars_list"]
    hosts = module.params["hosts"]
    cluster_name = module.params["cluster_name"]
    mp = {x["name_suffix"]: x["roles"] for x in vars_list["vars_list"]}
    ns_mp = {
        cluster_name + "-" + x["name_suffix"]: x.get("nameservice_id", "")
        for x in vars_list["vars_list"]
    }

    hd = defaultdict(list)
    for host in hosts:
        hd[host["key"]].append(host["value"])

    label_tuples = {
        cluster_name + "-" + k: (hd[cluster_name + "-" + k], v)
        for k, v in mp.items()
    }

    hdfs_ns_tuples = {h: ns_mp[k] for k, v in hd.items() for h in v}

    label_lists = [label(*v) for k, v in label_tuples.items()]
    result_string = str(stringify(label_lists, hdfs_ns_tuples))

    vmss_file = open(join(deploy_path, "conf/azure_vmss_to_hosts.conf"), "w")
    for key in hd:
        vmss_file.write("[" + key.replace("-", "_") + "]\n")
        for value in hd[key]:
            vmss_file.write(value)
            vmss_file.write("\n")
        vmss_file.write("\n")
    vmss_file.write("\n")
    vmss_file.close()

    module.exit_json(result=result_string)


if __name__ == "__main__":
    main()
