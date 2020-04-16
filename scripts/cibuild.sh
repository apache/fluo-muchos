#! /usr/bin/bash
set -e
echo "Running nose tests"
nosetests -w lib/
echo "Running Ansible-lint"
ansible-lint -x 204,301
echo "Ansible-lint returned OK"
echo "Running flake8 to check Python code"
flake8
echo "flake8 returned OK"
echo "Checking for files which have no newline at end of file"
git ls-files | tr '\n' '\0' | xargs -0 -L1 bash -c 'if test "$(grep --files-with-matches --binary-files=without-match --max-count=1 --regexp='.*' "$0")" && test "$(tail --bytes=1 "$0")"; then echo "No new line at end of $0."; false; fi'
echo "All tests passed!"
