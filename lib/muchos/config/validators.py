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


class _validator(object):
    def __init__(self, f, msg):
        self.f = f
        self.msg = msg

    def __call__(self, n):
        return self.f(n)

    def __str__(self):
        return self.msg


def greater_than(val):
    return _validator(lambda n: n > val, "must be greater than {}".format(val))


def less_than(val):
    return _validator(lambda n: n < val, "must be less than {}".format(val))


def equals(val):
    return _validator(lambda n: n == val, "must equal {}".format(val))


def contains(val):
    return _validator(lambda n: val in n, "must contain {}".format(val))


def is_in(val):
    return _validator(lambda n: n in val, "must be in {}".format(val))


def is_type(t):
    return _validator(
        lambda n: isinstance(n, t), "must be of type {}".format(t)
    )
