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
from pydoc import locate


# struct to hold information about ansible vars defined via decorators.
# var_name indicates the desired variable name
# class_name indicates the class name where the variable was defined
# property_name indicates the class property/function where the variable was
#               defined
class _ansible_var(object):
    def __init__(self, var_name, class_name, property_name, module_name):
        self.var_name = var_name
        self.class_name = class_name
        self.property_name = property_name
        self.module_name = module_name

    def __str__(self):
        return (
            "var_name={}, class_name={}, " "property_name={}, module_name={}"
        ).format(
            self.var_name,
            self.class_name,
            self.property_name,
            self.module_name,
        )


# each entry of _ansible_vars will contain a list of _ansible_var instances
_ansible_vars = dict(host=[], play=[], extra=[])


def get_ansible_vars(var_type, class_in_scope):
    # return variables for the complete class hierarchy
    return list(
        filter(
            lambda v: issubclass(
                class_in_scope, locate(v.module_name + "." + v.class_name)
            ),
            _ansible_vars.get(var_type),
        )
    )


# ansible hosts inventory variables
def ansible_host_var(name=None):
    return ansible_var_decorator("host", name)


# ansible group/all variables
def ansible_play_var(name=None):
    return ansible_var_decorator("play", name)


# ansible extra variables
def ansible_extra_var(name=None):
    return ansible_var_decorator("extra", name)


def ansible_var_decorator(var_type, name):
    def _decorator(func):
        ansible_var = _ansible_var(
            var_name=name if isinstance(name, str) else func.__name__,
            class_name=func.__qualname__.split(".")[0],
            property_name=func.__name__,
            module_name=func.__module__,
        )
        _ansible_vars[var_type].append(ansible_var)
        return func

    if callable(name):
        return _decorator(name)
    return _decorator


def default(val):
    def _default(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                res = func(*args, **kwargs)
            except:  # noqa
                return val
            else:
                if res is None or (isinstance(res, str) and len(res) == 0):
                    return val
                return res

        return wrapper

    return _default


def required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        if res in [None, 0, ""] or len(res) == 0:
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
            failed_checks = list(
                filter(lambda f: f(res) is not True, validators)
            )
            if len(failed_checks) > 0:
                raise Exception(
                    "{}={} checked validation {}".format(
                        func.__name__, res, [str(v) for v in failed_checks]
                    )
                )
            return res

        return wrapper

    return _validate


class ConfigMissingError(Exception):
    def __init__(self, name):
        super(ConfigMissingError, self).__init__(
            "{} is missing from the configuration".format(name)
        )
