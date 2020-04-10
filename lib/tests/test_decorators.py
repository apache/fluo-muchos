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

from unittest import TestCase

from muchos.config import decorators


class DecoratedThing(object):
    @property
    @decorators.ansible_host_var
    def host_var1(self):
        return "host_var1"

    @property
    @decorators.ansible_host_var(name="named_host_var2")
    def host_var2(self):
        return "named_host_var2"

    @property
    @decorators.ansible_play_var
    def play_var1(self):
        return "play_var1"

    @property
    @decorators.ansible_play_var(name="named_play_var2")
    def play_var2(self):
        return "named_play_var2"

    @property
    @decorators.ansible_extra_var
    def extra_var1(self):
        return "extra_var1"

    @property
    @decorators.ansible_extra_var(name="named_extra_var2")
    def extra_var2(self):
        return "named_extra_var2"

    @property
    @decorators.default("default_val")
    def default_val(self):
        return None

    @property
    @decorators.default(True)
    def default_boolean_val_True(self):
        return True

    @property
    @decorators.default(True)
    def default_boolean_val_False(self):
        return False

    @property
    @decorators.default(True)
    def default_missing_boolean_val(self):
        return None

    @property
    @decorators.required
    def required_val(self):
        return "required_val"

    @property
    @decorators.required
    def missing_required_val(self):
        return None


class DecoratorTests(TestCase):
    def _flatten_dict(d):
        return {(k, v) for k, v in d.items()}

    def test_decorators(self):
        thing = DecoratedThing()

        actual_host_vars = decorators.get_ansible_vars("host", type(thing))
        actual_play_vars = decorators.get_ansible_vars("play", type(thing))
        actual_extra_vars = decorators.get_ansible_vars("extra", type(thing))

        expected_host_vars = [
            decorators._ansible_var(
                "host_var1",
                "DecoratedThing",
                "host_var1",
                "tests.test_decorators",
            ),
            decorators._ansible_var(
                "named_host_var2",
                "DecoratedThing",
                "host_var2",
                "tests.test_decorators",
            ),
        ]

        expected_play_vars = [
            decorators._ansible_var(
                "play_var1",
                "DecoratedThing",
                "play_var1",
                "tests.test_decorators",
            ),
            decorators._ansible_var(
                "named_play_var2",
                "DecoratedThing",
                "play_var2",
                "tests.test_decorators",
            ),
        ]

        expected_extra_vars = [
            decorators._ansible_var(
                "extra_var1",
                "DecoratedThing",
                "extra_var1",
                "tests.test_decorators",
            ),
            decorators._ansible_var(
                "named_extra_var2",
                "DecoratedThing",
                "extra_var2",
                "tests.test_decorators",
            ),
        ]

        self.assertEquals(
            set([str(v) for v in expected_host_vars]),
            set([str(v) for v in actual_host_vars]),
        )

        self.assertEquals(
            set([str(v) for v in expected_play_vars]),
            set([str(v) for v in actual_play_vars]),
        )

        self.assertEquals(
            set([str(v) for v in expected_extra_vars]),
            set([str(v) for v in actual_extra_vars]),
        )

        self.assertEquals(thing.default_val, "default_val")
        self.assertEquals(thing.default_boolean_val_True, True)
        self.assertEquals(thing.default_boolean_val_False, False)
        self.assertEquals(thing.default_missing_boolean_val, True)
        self.assertEquals(thing.required_val, "required_val")
        with self.assertRaises(decorators.ConfigMissingError):
            thing.missing_required_val
