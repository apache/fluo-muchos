# Copyright 2014 Muchos authors (see AUTHORS)
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
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Utility methods
"""

import os
from os.path import isfile, join
import hashlib
import sys
from sys import stderr
import tarfile
import urllib2
from optparse import OptionParser


class EC2Type:
    def __init__(self, arch, ephemeral=1):
        self.arch = arch
        self.ephemeral = ephemeral


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
  "r3.2xlarge": EC2Type("hvm", 1),
  "r3.4xlarge": EC2Type("hvm", 1),
  "r3.8xlarge": EC2Type("hvm", 2),
  "r3.large": EC2Type("hvm", 1),
  "r3.xlarge": EC2Type("hvm", 1),
  "d2.xlarge": EC2Type("hvm", 3),
  "d2.2xlarge": EC2Type("hvm", 6),
}

# AMI given arch & region.  PVM arch currently not supported
ami_lookup = {
  "hvm": {"us-east-1": "ami-6d1c2007",
          "us-west-1": "ami-af4333cf",
          "us-west-2": "ami-d2c924b2",
          "eu-west-1": "ami-7abd0209",
          "eu-central-1": "ami-9bf712f4",
          "ap-southeast-1": "ami-f068a193",
          "ap-southeast-2": "ami-fedafc9d",
          "ap-northeast-1": "ami-eec1c380",
          "ap-northeast-2": "ami-c74789a9",
          "sa-east-1": "ami-26b93b4a"},
  "pvm": {"us-east-1": None,
          "us-west-1": None,
          "us-west-2": None,
          "eu-west-1": None,
          "eu-central-1": None,
          "ap-southeast-1": None,
          "ap-southeast-2": None,
          "ap-northeast-1": None,
          "sa-east-1": None},
}


def get_arch(instance_type):
    return instance_types.get(instance_type).arch


def get_num_ephemeral(instance_type):
    return instance_types.get(instance_type).ephemeral


def get_ami(instance_type, region):
    return ami_lookup.get(get_arch(instance_type)).get(region)


def setup_boto(lib_dir):
    # Download Boto if it's not already present in lib_dir
    version = "boto-2.34.0"
    md5 = "5556223d2d0cc4d06dd4829e671dcecd"
    url = "https://pypi.python.org/packages/source/b/boto/%s.tar.gz" % version
    if not os.path.exists(lib_dir):
        os.mkdir(lib_dir)
    boto_lib_dir = os.path.join(lib_dir, version)
    if not os.path.isdir(boto_lib_dir):
        tgz_file_path = os.path.join(lib_dir, "%s.tar.gz" % version)
        print "Downloading Boto from PyPi"
        download_stream = urllib2.urlopen(url)
        with open(tgz_file_path, "wb") as tgz_file:
            tgz_file.write(download_stream.read())
        with open(tgz_file_path) as tar:
            if hashlib.md5(tar.read()).hexdigest() != md5:
                print >> stderr, "ERROR: Got wrong md5sum for Boto"
                sys.exit(1)
        tar = tarfile.open(tgz_file_path)
        tar.extractall(path=lib_dir)
        tar.close()
        os.remove(tgz_file_path)
        print "Finished downloading Boto"
    sys.path.insert(0, boto_lib_dir)


def parse_args(hosts_dir, input_args=None):
    parser = OptionParser(
              usage="muchos [options] <action>\n\n"
              + "where <action> can be:\n"
              + "  launch     Launch cluster in EC2\n"
              + "  status     Check status of EC2 cluster\n"
              + "  setup      Set up cluster\n"
              + "  sync       Sync ansible directory on cluster proxy node\n"
              + "  config     Print configuration for that cluster. Requires '-p'. Use '-p all' for all config.\n"
              + "  ssh        SSH to cluster proxy node\n"
              + "  kill       Kills processes on cluster started by Muchos\n"
              + "  wipe       Wipes cluster data and kills processes\n"
              + "  terminate  Terminate EC2 cluster",
              add_help_option=False)
    parser.add_option("-c", "--cluster", dest="cluster", help="Specifies cluster")
    parser.add_option("-p", "--property", dest="property", help="Specifies property to print (if using 'config' action)"
                                                                ". Set to 'all' to print every property")
    parser.add_option("-h", "--help", action="help", help="Show this help message and exit")

    if input_args:
        (opts, args) = parser.parse_args(input_args)
    else:
        (opts, args) = parser.parse_args()

    if len(args) == 0:
        print "ERROR - You must specify on action"
        return
    action = args[0]

    if action == 'launch' and not opts.cluster:
        print "ERROR - You must specify a cluster if using launch command"
        return

    clusters = [f for f in os.listdir(hosts_dir) if isfile(join(hosts_dir, f))]

    if not opts.cluster:
        if len(clusters) == 0:
            print "ERROR - No clusters found in conf/hosts or specified by --cluster option"
            return
        elif len(clusters) == 1:
            opts.cluster = clusters[0]
        else:
            print "ERROR - Multiple clusters {0} found in conf/hosts/. " \
                  "Please pick one using --cluster option".format(clusters)
            return

    if action == 'config' and not opts.property:
        print "ERROR - For config action, you must set -p to a property or 'all'"
        return

    return opts, action, args[1:]
