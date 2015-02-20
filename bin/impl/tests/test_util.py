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

from fluo_deploy.util import get_image_id, get_arch

def test_util():
  assert get_arch('t1.micro') == 'pvm'
  assert get_arch('m1.large') == 'pvm'
  assert get_arch('m3.large') == 'hvm'
  assert get_arch('bad') is None

  assert get_image_id('m1.large') == 'ami-246ed34c'
  assert get_image_id('m3.large') == 'ami-b66ed3de'
  assert get_image_id('bad') is None
