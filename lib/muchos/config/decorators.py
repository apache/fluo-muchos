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

from collections.abc import Iterable
from functools import wraps


_host_vars = []
_play_vars = []
_extra_vars = []
_ansible_vars = dict(
    host=[],
    play=[],
    extra=[]
)

def get_ansible_vars(var_type):
    return _ansible_vars.get(var_type)

# ansible hosts inventory variables
def ansible_host_var(name=None):
    return ansible_var_decorator('host', name)

# ansible group/all variables
def ansible_play_var(name=None):
    return ansible_var_decorator('play', name)

# ansible extra variables
def ansible_extra_var(name=None):
    return ansible_var_decorator('extra', name)

def ansible_var_decorator(var_type, name):
    def _decorator(func):
        if getattr(func, '__isabstractmethod__', False):
            raise Exception("{}: cannot decorate an abstract method as play_var".format(func.__qualname__))

        _ansible_vars[var_type].append((name if isinstance(name, str) else func.__name__, func.__qualname__.split('.')[0], func.__name__))
        return func

    if callable(name):
        return _decorator(name)
    return _decorator

def default(val):
    def _default(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            res = func(*args, **kwargs)
            if res in [None, 0, ''] or len(res) == 0:
                return val
            return res
        return wrapper
    return _default

def required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        if res in [None, 0, ''] or len(res) == 0:
            raise ConfigMissingError(func.__name__)
        return res
    return wrapper

def is_valid(validators):
    if not isinstance(validators, Iterable):
        validators = [validators]
    def _validate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            res = func(*args, **kwargs)
            failed_checks = list(filter(lambda f: f(res) is not True, validators))
            if len(failed_checks) > 0:
                raise Exception("{}={} checked validation {}".format(
                    func.__name__, res,
                    [str(v) for v in failed_checks]))
            return res
        return wrapper
    return _validate

class ConfigMissingError(Exception):
    def __init__(self, name):
        super(ConfigMissingError, self).__init__("{} is missing from the configuration".format(name))

