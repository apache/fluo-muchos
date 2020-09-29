<!--
Licensed to the Apache Software Foundation (ASF) under one or more
contributor license agreements.  See the NOTICE file distributed with
this work for additional information regarding copyright ownership.
The ASF licenses this file to You under the Apache License, Version 2.0
(the "License"); you may not use this file except in compliance with
the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Contributors Guide

If you believe that you have found a bug, please search for an existing [issue](https://github.com/apache/fluo-muchos/issues) to see if it has already been reported. For simple changes, its ok to just submit a pull request without an issue.

## Muchos Testing

Muchos has unit tests. To run them, first install required packages:
```
    pip install -r ./lib/requirements.txt
```
The following command runs the unit tests:
```
    nosetests -w lib/
```

## Before you submit a PR

If you are modifying any of the Python code in this project, please use [Black](https://github.com/psf/black) to enforce that Python code found under the [lib](https://github.com/apache/fluo-muchos/tree/main/lib) folder is formatted correctly. Before submitting a PR, please ensure that you have used Black to format the code with max line length set to 79 as below (it is to be run from the repo root):
```
black lib --line-length 79
```

The [CI](https://github.com/apache/fluo-muchos/tree/main/.github/workflows/ci.yaml) for this project runs tools to detect common coding issues with Python and Ansible files. Rather than wait for the CI to flag any issues with your work, please run the [cibuild](https://github.com/apache/fluo-muchos/tree/main/scripts/cibuild.sh) script on your dev machine, which in turn runs the following tools:
- [flake8](https://github.com/pycqa/flake8) to validate that the Python code in the project conforms to known good practices.
- [Ansible-lint](https://github.com/ansible/ansible-lint/) prior to submitting a PR. This will ensure that you align with known good practices. Please also review the guidance on [false positives](https://docs.ansible.com/ansible-lint/rules/rules.html#false-positives-skipping-rules) from Ansible-lint.

Please ensure that you address issues flagged by the above CI build script before creating a PR.

## Review

- We welcome reviews from anyone. Any committer can approve and merge the changes.
- Reviewers will likely have questions and comments. They may use terms such as those in [RFC2119](https://tools.ietf.org/html/rfc2119).
