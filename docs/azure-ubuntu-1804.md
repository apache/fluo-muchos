Tips for running Muchos for Azure under Ubuntu 18.04
----------------------------------------------------

For Azure, Muchos sets up an AlmaLinux 9 based cluster by default, but Muchos itself can
be run on other flavors of Linux. If you wish to run Muchos under Ubuntu 18.04 and have it
set up an Azure cluster, then the following steps can get you on your way.

```bash
# Install Azure CLI.  See the Azure documentation.
# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-apt?view=azure-cli-latest

# Install Ansible Azure for Python 3.  The main reason these tips were written
# was to save you time on the following steps.  Muchos is tested with Python 3.11 and above.
# If python-pip and pip were installed and used, those would go against Python 2
# and would not work.
sudo apt install python3-pip
sudo pip3 install -r lib/requirements.txt
# Current versions of Ansible separate out the Azure-specific modules into a
# separate "collection". To install that, and associated pre-requisites, a helper
# script has been provided. Please be sure to execute these scripts:
./scripts/install-ansible-for-azure
./scripts/install-ansible-collections
```

A virtual python environment is not needed in Ubuntu, but can be useful considering
the variety of dependencies installed locally for Azure.
