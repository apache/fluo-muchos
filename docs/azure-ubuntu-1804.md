Tips for running Muchos for Azure under Ubuntu 18.04
----------------------------------------------------

Muchos sets up a Centos cluster, but it does not have to run in Centos.  If you
wish to run Muchos under Ubuntu 18.04 and have it set up an Azure cluster, then
the following steps can get you on your way.

```bash
# Install Azure CLI.  See the Azure documentation.
# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-apt?view=azure-cli-latest

# Install Ansible Azure for Python 3.  The main reason these tips were written
# was to save you time on the following steps.  Muchos is tested with Python 3.9 and above.
# If python-pip and pip were installed and used, those would go against Python 2
# and would not work.
sudo apt install python3-pip
sudo pip3 install -r lib/requirements.txt
# Current versions of Ansible separate out the Azure-specific modules into a
# separate "collection". To install that, and associated pre-requisites, a helper
# script has been provided. Please be sure to execute this script:
./scripts/install-ansible-for-azure
```

A virtual python environment is not needed in Ubuntu.  The instructions that
mention that are targeted for Centos 7.  The version of Python 3 and pip3 that
ship with Ubuntu 18.04 suffice.
