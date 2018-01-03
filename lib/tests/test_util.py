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

from muchos.util import get_arch, parse_args, get_ami, get_ephemeral_devices


def test_util():
    assert set(get_ephemeral_devices('m3.large')) == set(['/dev/xvdb'])
    assert set(get_ephemeral_devices('m3.xlarge')) == set(['/dev/xvdb', '/dev/xvdc'])

    assert set(get_ephemeral_devices('i3.xlarge')) == set(['/dev/nvme0n1'])
    assert set(get_ephemeral_devices('i3.4xlarge')) == set(['/dev/nvme0n1','/dev/nvme1n1'])

    assert get_arch('m1.large') == 'pvm'
    assert get_arch('m3.large') == 'hvm'

    assert get_ami('m3.large', 'us-east-1') == 'ami-6d1c2007'
    assert get_ami('m1.large', 'us-east-1') is None

    hosts_dir = '../conf/hosts'
    assert parse_args(hosts_dir, ['launch']) is None
    assert parse_args(hosts_dir, ['launch', 'mycluster']) is None
    assert parse_args(hosts_dir, ['-c', 'mycluster', 'launch']) is not None

    hosts_dir = '../conf/hosts/example'
    assert parse_args(hosts_dir, ['setup']) is not None
    assert parse_args(hosts_dir, ['config']) is None
    assert parse_args(hosts_dir, ['-p', 'all', 'config']) is not None
