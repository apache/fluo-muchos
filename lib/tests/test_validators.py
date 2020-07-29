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

from muchos.config import validators
from muchos.config.decorators import is_valid


class ValidateThis(object):
    @property
    @is_valid(validators.greater_than(5))
    def fourNotGreaterThanFive(self):
        return 4

    @property
    @is_valid(validators.greater_than(5))
    def fiveNotGreaterThanFive(self):
        return 5

    @property
    @is_valid(validators.greater_than(5))
    def sixGreaterThanFive(self):
        return 6

    @property
    @is_valid(validators.less_than(5))
    def fourLessThanFive(self):
        return 4

    @property
    @is_valid(validators.less_than(5))
    def fiveNotLessThanFive(self):
        return 5

    @property
    @is_valid(validators.less_than(5))
    def sixNotLessThanFive(self):
        return 6

    @property
    @is_valid(validators.equals(5))
    def fourNotEqualFive(self):
        return 4

    @property
    @is_valid(validators.equals(5))
    def fiveEqualFive(self):
        return 5

    @property
    @is_valid(validators.equals(5))
    def sixeNotEqualFive(self):
        return 6

    @property
    @is_valid(validators.contains(5))
    def containsFive(self):
        return [4, 5, 6]

    @property
    @is_valid(validators.contains(5))
    def notContainsFive(self):
        return []

    @property
    @is_valid(validators.is_in([5]))
    def fourNotInListOfFive(self):
        return 4

    @property
    @is_valid(validators.is_in([5]))
    def fiveInListOfFive(self):
        return 5

    @property
    @is_valid(validators.is_in([5]))
    def sixNotInListOfFive(self):
        return 6

    @property
    @is_valid(validators.is_type(str))
    def intIsNotString(self):
        return 5

    @property
    @is_valid(validators.is_type(str))
    def stringIsString(self):
        return "some string"


class ValidationTests(TestCase):
    def test_validators(self):
        thing = ValidateThis()

        with self.assertRaises(Exception):
            thing.fourNotGreaterThanFive

        with self.assertRaises(Exception):
            thing.fiveNotGreaterThanFive

        self.assertEqual(thing.sixGreaterThanFive, 6)

        self.assertEqual(thing.fourLessThanFive, 4)

        with self.assertRaises(Exception):
            thing.fiveNotLessThanFive

        with self.assertRaises(Exception):
            thing.sixNotLessThanFive

        with self.assertRaises(Exception):
            thing.fourNotEqualFive

        self.assertEqual(thing.fiveEqualFive, 5)

        with self.assertRaises(Exception):
            thing.sixeNotEqualFive

        self.assertEqual(thing.containsFive, [4, 5, 6])

        with self.assertRaises(Exception):
            thing.notContainsFive

        with self.assertRaises(Exception):
            thing.fourNotInListOfFive

        self.assertEqual(thing.fiveInListOfFive, 5)

        with self.assertRaises(Exception):
            thing.sixNotInListOfFive

        with self.assertRaises(Exception):
            thing.intIsNotString

        self.assertEqual(thing.stringIsString, "some string")
