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
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Utility methods 
"""

import os
import hashlib
import sys
from sys import stderr
import tarfile
import urllib2
from optparse import OptionParser

instance_types = {
  "c1.medium": "pvm",
  "c1.xlarge": "pvm",
  "c3.2xlarge": "pvm",
  "c3.4xlarge": "pvm",
  "c3.8xlarge": "pvm",
  "c3.large": "pvm",
  "c3.xlarge": "pvm",
  "cc1.4xlarge": "hvm",
  "cc2.8xlarge": "hvm",
  "cg1.4xlarge": "hvm",
  "cr1.8xlarge": "hvm",
  "hi1.4xlarge": "pvm",
  "hs1.8xlarge": "pvm",
  "i2.2xlarge": "hvm",
  "i2.4xlarge": "hvm",
  "i2.8xlarge": "hvm",
  "i2.xlarge": "hvm",
  "m1.large": "pvm",
  "m1.medium": "pvm",
  "m1.small": "pvm",
  "m1.xlarge": "pvm",
  "m2.2xlarge": "pvm",
  "m2.4xlarge": "pvm",
  "m2.xlarge": "pvm",
  "m3.2xlarge": "hvm",
  "m3.large": "hvm",
  "m3.medium": "hvm",
  "m3.xlarge": "hvm",
  "r3.2xlarge": "hvm",
  "r3.4xlarge": "hvm",
  "r3.8xlarge": "hvm",
  "r3.large": "hvm",
  "r3.xlarge": "hvm",
  "t1.micro": "pvm",
  "t2.medium": "hvm",
  "t2.micro": "hvm",
  "t2.small": "hvm",
}

def get_arch(instance_type):
  return instance_types.get(instance_type)

def get_image_id(instance_type):
  arch = get_arch(instance_type)
  if arch == "hvm":
    return "ami-b66ed3de"
  elif arch == "pvm":
    return "ami-246ed34c"
  else:
    return None

def exit(msg):
  print msg
  sys.exit(1)

def setup_boto(lib_dir):
  # Download Boto if it's not already present in lib_dir
  version = "boto-2.35.2"
  md5 = "3a421325aa2751ca8f5ab90eb9d24da9"
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

def parse_args(input=None):
  parser = OptionParser(
            usage="fluo-deploy [options] <action> <cluster_name>"
            + "\n\nwhere <action> can be:\n  launch - Launch cluster in EC2\n  status - Check status of EC2 cluster\n"
            + "  setup - Setup Fluo and its dependencies on cluster\n  ssh - SSH to cluster leader node\n"
            + "  kill - Kill Fluo and its dependencies on cluster\n  terminate - Terminate EC2 cluster",
            add_help_option=False)
  parser.add_option(
    "-h", "--help", action="help",
    help="Show this help message and exit")

  if input:
    (opts, args) = parser.parse_args(input)
  else:
    (opts, args) = parser.parse_args()

  if len(args) != 2:
    parser.print_help()
    sys.exit(1)

  (action, cluster_name) = args

  return (opts, action, cluster_name)

