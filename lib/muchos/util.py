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

"""
Utility methods
"""

import os
import sys
from os.path import isfile, join
from optparse import OptionParser


class EC2Type:
    def __init__(self, arch, ephemeral=1, has_nvme=False):
        self.arch = arch
        self.ephemeral = ephemeral
        self.has_nvme = has_nvme


AMI_HELP_MSG = """PLEASE NOTE - If you have accepted the software terms for CentOS 7 and still get an error,
this could be due to CentOS releasing new images of CentOS 7.  When this occurs, the old images
are no longer available to new users.  If you think this is the case, go to the CentOS 7 product
page on AWS Marketplace at the URL below to find the latest AMI:

    https://aws.amazon.com/marketplace/pp/B00O7WM7QW

On the product page, find the latest AMI ID for your EC2 region. This should be used to set the 'aws_ami'
property in your muchos.props.  After setting the 'aws_ami' property, run the launch command again.
"""  # noqa

instance_types = {
    "c1.medium": EC2Type("pvm"),
    "c1.xlarge": EC2Type("pvm", 4),
    "c3.2xlarge": EC2Type("pvm", 2),
    "c3.4xlarge": EC2Type("pvm", 2),
    "c3.8xlarge": EC2Type("pvm", 2),
    "c3.large": EC2Type("pvm", 2),
    "c3.xlarge": EC2Type("pvm", 2),
    "cc2.8xlarge": EC2Type("hvm", 4),
    "cg1.4xlarge": EC2Type("hvm", 2),
    "cr1.8xlarge": EC2Type("hvm", 2),
    "hi1.4xlarge": EC2Type("pvm", 2),
    "hs1.8xlarge": EC2Type("pvm", 24),
    "i2.2xlarge": EC2Type("hvm", 2),
    "i2.4xlarge": EC2Type("hvm", 4),
    "i2.8xlarge": EC2Type("hvm", 8),
    "i2.xlarge": EC2Type("hvm"),
    "i3.large": EC2Type("hvm", 1, True),
    "i3.xlarge": EC2Type("hvm", 1, True),
    "i3.2xlarge": EC2Type("hvm", 1, True),
    "i3.4xlarge": EC2Type("hvm", 2, True),
    "m1.large": EC2Type("pvm", 2),
    "m1.medium": EC2Type("pvm"),
    "m1.small": EC2Type("pvm"),
    "m1.xlarge": EC2Type("pvm", 4),
    "m2.2xlarge": EC2Type("pvm", 1),
    "m2.4xlarge": EC2Type("pvm", 2),
    "m2.xlarge": EC2Type("pvm"),
    "m3.2xlarge": EC2Type("hvm", 2),
    "m3.large": EC2Type("hvm"),
    "m3.medium": EC2Type("hvm"),
    "m3.xlarge": EC2Type("hvm", 2),
    "m5d.large": EC2Type("hvm", 1, True),
    "m5d.xlarge": EC2Type("hvm", 1, True),
    "m5d.2xlarge": EC2Type("hvm", 1, True),
    "m5d.4xlarge": EC2Type("hvm", 2, True),
    "m5d.12xlarge": EC2Type("hvm", 2, True),
    "m5d.24xlarge": EC2Type("hvm", 4, True),
    "r3.2xlarge": EC2Type("hvm", 1),
    "r3.4xlarge": EC2Type("hvm", 1),
    "r3.8xlarge": EC2Type("hvm", 2),
    "r3.large": EC2Type("hvm", 1),
    "r3.xlarge": EC2Type("hvm", 1),
    "d2.xlarge": EC2Type("hvm", 3),
    "d2.2xlarge": EC2Type("hvm", 6),
    "d2.4xlarge": EC2Type("hvm", 12),
    "d2.8xlarge": EC2Type("hvm", 24),
}


def verify_type(instance_type):
    if instance_type not in instance_types:
        print(
            "ERROR - EC2 instance type '{}' is currently "
            "not supported!".format(instance_type)
        )
        print("This is probably due to the instance type being EBS-only.")
        print("Below is a list of supported instance types:")
        for key in instance_types:
            print(key)
        sys.exit(1)


def get_arch(instance_type):
    verify_type(instance_type)
    return instance_types.get(instance_type).arch


def get_ephemeral_devices(instance_type):
    verify_type(instance_type)
    devices = []
    ec2_type = instance_types.get(instance_type)

    start = 0
    if instance_type.startswith("m5d"):
        start = 1

    for i in range(start, ec2_type.ephemeral + start):
        if ec2_type.has_nvme:
            devices.append("/dev/nvme" + str(i) + "n1")
        else:
            devices.append("/dev/xvd" + chr(ord("b") + i))

    return devices


def get_block_device_map(instance_type):
    verify_type(instance_type)

    bdm = [{"DeviceName": "/dev/sda1", "Ebs": {"DeleteOnTermination": True}}]

    ec2_type = instance_types.get(instance_type)
    if not ec2_type.has_nvme:
        for i in range(0, ec2_type.ephemeral):
            device = {
                "DeviceName": "/dev/xvd" + chr(ord("b") + i),
                "VirtualName": "ephemeral" + str(i),
            }
            bdm.append(device)

    return bdm


def parse_args(hosts_dir, input_args=None):
    parser = OptionParser(
        usage="muchos [options] <action>\n\n"
        + "where <action> can be:\n"
        + "  launch           Launch cluster in Azure or EC2\n"
        + "  status           Check status of Azure or EC2 cluster\n"
        + "  setup            Set up cluster\n"
        + "  sync             Sync ansible directory on cluster proxy node\n"
        + "  config           Print configuration for that cluster. "
        "Requires '-p'. Use '-p all' for all config.\n"
        + "  stop             Stops instance\n"
        + "  start            Starts instance\n"
        + "  ssh              SSH to cluster proxy node\n"
        + "  kill             Kills processes on cluster started by Muchos\n"
        + "  wipe             Wipes cluster data and kills processes\n"
        + "  terminate        Terminate EC2 cluster\n"
        + "  cancel_shutdown  Cancels automatic shutdown of EC2 cluster",
        add_help_option=False,
    )
    parser.add_option(
        "-c", "--cluster", dest="cluster", help="Specifies cluster"
    )
    parser.add_option(
        "-p",
        "--property",
        dest="property",
        help="Specifies property to print (if using 'config' action)"
        ". Set to 'all' to print every property",
    )
    parser.add_option(
        "-h", "--help", action="help", help="Show this help message and exit"
    )

    if input_args:
        (opts, args) = parser.parse_args(input_args)
    else:
        (opts, args) = parser.parse_args()

    if len(args) == 0:
        print("ERROR - You must specify on action")
        return
    action = args[0]

    if action == "launch" and not opts.cluster:
        print("ERROR - You must specify a cluster if using launch command")
        return

    clusters = [f for f in os.listdir(hosts_dir) if isfile(join(hosts_dir, f))]

    if not opts.cluster:
        if len(clusters) == 0:
            print(
                "ERROR - No clusters found in conf/hosts "
                "or specified by --cluster option"
            )
            return
        elif len(clusters) == 1:
            opts.cluster = clusters[0]
        else:
            print(
                "ERROR - Multiple clusters {0} found in conf/hosts/. "
                "Please pick one using --cluster option".format(clusters)
            )
            return

    if action == "config" and not opts.property:
        print(
            "ERROR - For config action, you must set -p to a property or 'all'"
        )
        return

    return opts, action, args[1:]
