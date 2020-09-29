![Muchos][logo]
---
[![Build Status][ci]][ga] [![Apache License][li]][ll]

**Muchos automates setting up [Apache Accumulo][accumulo] or [Apache Fluo][fluo] (and their dependencies) on a cluster**

Muchos makes it easy to launch a cluster in Amazon's EC2 or Microsoft Azure and deploy Accumulo or Fluo to it. Muchos
enables developers to experiment with Accumulo or Fluo in a realistic, distributed environment.
Muchos installs all software using tarball distributions which makes its easy to experiment
with the latest versions of Accumulo, Hadoop, Zookeeper, etc without waiting for downstream packaging.

Muchos is not recommended at this time for production environments as it has no support for updating
and upgrading dependencies. It also has a wipe command that is great for testing but dangerous for
production environments.

Muchos is structured into two high level components:

 * [Ansible] scripts that install and configure Fluo and its dependencies on a cluster.
 * Python scripts that push the Ansible scripts from a local development machine to a cluster and
   run them. These Python scripts can also optionally launch a cluster in EC2 using [boto] or in Azure using Azure CLI.

Checkout [Uno] for setting up Accumulo or Fluo on a single machine.

## Requirements

### Common

Muchos requires the following common components for installation and setup:

* Python 3 with a virtual environment setup
Create a Python 3 environment and switch to it. (We tested using Python 3.6.8,
but this should work in later versions as well. If you encounter problems,
please file an issue.)
```bash
cd ~
python3.6 -m venv env
source env/bin/activate
```
* `ssh-agent` installed and running and ssh-agent forwarding.  Note that this may
also require the creation of SSH public-private [key pair](https://help.github.com/en/articles/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent).
```bash
eval $(ssh-agent -s)
ssh-add ~/.ssh/id_rsa
```
* Git (current version)

### EC2

Muchos requires the following for EC2 installations:

* [awscli] (version 2) & [boto3] libraries - Install using `pip3 install awscli2 boto3 --upgrade`
* Note: if using Ubuntu you may need to install botocore separately using `pip3 install awscli boto3 botocore`
* An AWS account with your SSH public key uploaded. When you configure [muchos.props], set `key.name`
  to name of your key pair in AWS.
* `~/.aws` [configured][aws-config] on your machine. Can be created manually or using [aws configure][awscli-config].

### Azure

Muchos requires the following for Azure installations:

* [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest) must be installed,
  configured and authenticated to an Azure subscription. Please note - you should install
  [Azure CLI 2.0.69](https://packages.microsoft.com/yumrepos/azure-cli/azure-cli-2.0.69-1.el7.x86_64.rpm) on CentOS.
  Higher versions of Azure CLI are unsupported for Muchos on CentOS at this time until
  [this issue](https://github.com/Azure/azure-cli/issues/10128) in the Azure CLI 2.0.70 is fixed.
  Example command to install Azure CLI 2.0.69 on CentOS is below:
```bash
wget https://packages.microsoft.com/yumrepos/azure-cli/azure-cli-2.0.69-1.el7.x86_64.rpm
sudo yum install azure-cli-2.0.69-1.el7.x86_64.rpm
```
* An Azure account with permissions to either use an existing or create new Resource Groups, Virtual Networks and Subnets
* A machine which can connect to securely deploy the cluster in Azure.
* Install [Ansible for Azure](https://docs.microsoft.com/en-us/azure/virtual-machines/linux/ansible-install-configure) within
  the Python virtual environment by using `pip install ansible[azure]`

When running Muchos under Ubuntu 18.04, checkout these [tips](docs/azure-ubuntu-1804.md).

## Quickstart

The following commands will install Muchos, launch a cluster, and setup/run Accumulo:

```sh
git clone https://github.com/apache/fluo-muchos.git

cd fluo-muchos/
cp conf/muchos.props.example conf/muchos.props
vim conf/muchos.props                                   # Edit to configure Muchos cluster
./bin/muchos launch -c mycluster                        # Launches Muchos cluster in EC2 or Azure
./bin/muchos setup                                      # Set up cluster and start Accumulo
```

The `launch` command will create a cluster with the name specified in the command (e.g. 'mycluster'). The `setup`
command can be run repeatedly to fix any failures and will not repeat successful operations.

After your cluster is launched, SSH to it using the following command:

```sh
./bin/muchos ssh
```

Run the following command to terminate your cluster. WARNING: All cluster data will be lost.

```sh
./bin/muchos terminate
```

Please continue reading for more detailed Muchos instructions.

## Launching an EC2 cluster

Before launching a cluster, you will need to complete the requirements above, clone the Muchos repo, and
create [muchos.props]. If you want to give others access to your cluster, add
their public keys to a file named `keys` in your `conf/` directory.  During the setup of your
cluster, this file will be appended on each node to the `~/.ssh/authorized_keys` file for the user
set by the `cluster.username` property.

### Configuring the AMI

You might also need to configure the `aws_ami` property in [muchos.props]. Muchos by default uses a free
CentOS 7 image that is hosted in the AWS marketplace but managed by the
CentOS organization. If you have never used this image in EC2 before, you will need to go to the
[CentOS 7 product page][centos7] to accept the software terms. If this is not done, you will get an
error when you try to launch your cluster. By default, the `aws_ami` property is set to an AMI in `us-east-1`.
You will need to changes this value if a newer image has been released or if you are running in different region
than `us-east-1`.

### Launching the cluster

After following the steps above, run the following command to launch an EC2 cluster called `mycluster`:

    ./bin/muchos launch -c mycluster

After your cluster has launched, you do not have to specify a cluster anymore using `-c` (unless you
have multiple clusters running).

Run the following command to confirm that you can ssh to the leader node:

    ./bin/muchos ssh

You can check the status of the nodes using the EC2 Dashboard or by running the following command:

    ./bin/muchos status

## Launching an Azure cluster

Before launching a cluster, you will need to complete the requirements for Azure above, clone the Muchos repo, and
create [muchos.props] by making a copy of existing [muchos.props.example]. If you want to give others access to your
cluster, add their public keys to a file named `keys` in your `conf/` directory.  During the setup of your cluster,
this file will be appended on each node to the `~/.ssh/authorized_keys` file for the user set by the
`cluster.username` property.  You will also need to ensure you have authenticated to Azure and set the target
subscription using the [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/manage-azure-subscriptions-azure-cli?view=azure-cli-latest).

Muchos by default uses a CentOS 7 image that is hosted in the Azure marketplace. The Azure Linux Agent is already
pre-installed on the Azure Marketplace images and is typically available from the distribution's package repository.
Azure requires that the publishers of the endorsed Linux distributions regularly update their images in the Azure
Marketplace with the latest patches and security fixes, at a quarterly or faster cadence. Updated images in the Azure
Marketplace are available automatically to customers as new versions of an image SKU.

Edit the values in the sections within [muchos.props] as below
Under the `general` section, edit following values as per your configuration
* `cluster_type = azure`
* `cluster_user` should be set to the name of the administrative user
* `proxy_hostname` (optional) is the name of the machine which has access to the cluster VNET

Under the `azure` section, edit following values as per your configuration:
* `resource_group` to provide the resource-group name for the cluster deployment. A new resource group with
  this name will be created if it doesn't already exist
* `vnet` to provide the name of the VNET that your cluster nodes should use. A new VNET with this name will be
  created if it doesn't already exist
* `subnet` to provide a name for the subnet within which the cluster resources will be deployed
* `numnodes` to change the cluster size in terms of number of nodes deployed
* `data_disk_count` to specify how many persistent data disks are attached to each node and will be used by HDFS.
   If you would prefer to use ephemeral / storage for Azure clusters, please follow [these steps](docs/azure-ephemeral-disks.md).
* `vm_sku` to specify the VM size to use. You can choose from the
  [available VM sizes](https://docs.microsoft.com/en-us/azure/virtual-machines/linux/sizes-general).
* `use_adlsg2` to use Azure Data Lake Storage(ADLS) Gen2 as datastore for Accumulo
  [ADLS Gen2 Doc](https://docs.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-introduction).
  [Setup ADLS Gen2 as datastore for Accumulo](https://accumulo.apache.org/blog/2019/10/15/accumulo-adlsgen2-notes.html).
* `az_oms_integration_needed` to implement Log Analytics workspace, Dashboard & Azure Monitor Workbooks
  [Create Log Analytics workspace](https://docs.microsoft.com/en-us/azure/azure-monitor/learn/quick-create-workspace).
  [Create and Share dashboards](https://docs.microsoft.com/en-us/azure/azure-portal/azure-portal-dashboards).
  [Azure Monitor Workbooks](https://docs.microsoft.com/en-us/azure/azure-monitor/platform/workbooks-overview).

Within Azure the `nodes` section is auto populated with the hostnames and their default roles.

After following the steps above, run the following command to launch an Azure VMSS cluster called `mycluster`
(where 'mycluster' is the name assigned to your cluster):
```bash
.bin/muchos launch -c `mycluster` # Launches Muchos cluster in Azure
```

## Set up the cluster

Once your cluster is built in EC2 or Azure, the `./bin/muchos setup` command will set up your cluster and
start Hadoop, Zookeeper & Accumulo.  It will download release tarballs of Fluo, Accumulo, Hadoop, etc. The
versions of these tarballs are specified in [muchos.props] and can be changed if desired.

Optionally, Muchos can setup the cluster using an Accumulo or Fluo tarball that is placed in the
`conf/upload` directory of Muchos. This option is only necessary if you want to use an unreleased
version of Fluo or Accumulo. Before running the `muchos setup` command, you should confirm that the
hash (typically SHA-512 or SHA-256) of your tarball matches what is set in [conf/checksums][checksums].
Run the command `shasum -a 512 /path/to/tarball` on your tarball to determine its hash.
The entry in [conf/checksums][checksums] can optionally include the algorithm as a prefix. If the algorithm
is not specified then Muchos will infer the algorithm based on the length of the hash. Currently Muchos
supports using sha512 / sha384 / sha256 / sha224 / sha1 / md5 hashes for the checksum.

The `muchos setup` command will install and start Accumulo, Hadoop, and Zookeeper.  The optional
services below will only be set up if configured in the `[nodes]` section of [muchos.props]:

1. `fluo` - Fluo only needs to be installed and configured on a single node in your cluster as Fluo
applications are run in YARN.  If set as a service, `muchos setup` will install and partially
configure Fluo but not start it.  To finish setup, follow the steps in the 'Run a Fluo application'
section below.

2. `metrics` - The Metrics service installs and configures collectd, InfluxDB and Grafana.  Cluster
metrics are sent to InfluxDB using collectd and are viewable in Grafana.  If Fluo is running, its
metrics will also be viewable in Grafana.

3. `spark` - If specified on a node, Apache Spark will be installed on all nodes and the Spark History
server will be run on this node.

4. `mesosmaster` - If specified, a Mesos master will be started on this node and Mesos slaves will
be started on all workers nodes. The Mesos status page will be viewable at
`http://<MESOS_MASTER_NODE>:5050/`. Marathon will also be started on this node and will be viewable
at `http://<MESOS_MASTER_NODE>:8080/`.

5. `client` - Used to specify a client node where no services are run but libraries are installed to
run Accumulo/Hadoop clients.

6. `swarmmanager` - Sets up [Docker swarm] with the manager on this node and joins all worker nodes
to this swarm. When this is set, docker will be installed on all nodes of the cluster. It is
recommended that the swarm manager is specified on a worker node as it runs docker containers. Check
out [Portainer] if you want to run a management UI for your swarm cluster.

7. `elkserver` - Sets up the Elasticsearch, Logstash, and Kibana stack. This allows logging data to be search, analyzed, and visualized in real time.

If you run the `muchos setup` command and a failure occurs, you can repeat the command until setup
completes. Any work that was successfully completed will not be repeated. While some setup steps can
take over a minute, use `ctrl-c` to stop setup if it hangs for a long time. Just remember to run
`muchos setup` again to finish setup.

## Manage the cluster

The `setup` command is idempotent. It can be run again on a working cluster. It will not change the
cluster if everything is configured and running correctly. If a process has stopped, the `setup`
command will restart the process.

The `./bin/muchos wipe` command can be used to wipe all data from the cluster and kill any running
processes. After running the `wipe` command, run the `setup` command to start a fresh cluster.

If you set `proxy_socks_port` in your [muchos.props], a SOCKS proxy will be created on that port
when you use `muchos ssh` to connect to your cluster. If you add a proxy management tool to your
browser and whitelist `http://leader*`, `http://worker*` and `http://metrics*` to redirect traffic
to your proxy, you can view the monitoring & status pages below in your browser. Please note - The
hosts in the URLs below match the configuration in [nodes] of `muchos.prop.example` and may be
different for your cluster.

 * NameNode status - [http://leader1:9870/](http://leader1:9870/)
 * ResourceManger status - [http://leader2:8088/cluster](http://leader2:8088/cluster)
 * Accumulo monitor - [http://leader3:9995/](http://leader3:9995/)
 * Spark History Server - [http://leader2:18080/](http://leader2:18080/)
 * Grafana Metrics and Monitoring - [http://metrics:3000/](http://metrics:3000/)
 * Mesos status - [http://leader1:5050/](http://leader1:5050/) (if `mesosmaster` configured on leader1)
 * Marathon status - [http://leader1:8080/](http://leader1:8080/) (if `mesosmaster` configured on leader1)
 * Kibana status - [http://leader1:5601/](http://leader1:5601) (But Kibana is configured on all nodes)

## Run a Fluo application

Running an example Fluo application like [WebIndex], [Phrasecount], or [Stresso] is easy
with Muchos as it configures your shell with common environment variables. To run an example
application, SSH to a node on cluster where Fluo is installed and clone the example repo:

```sh
./bin/muchos ssh                      # SSH to cluster proxy node
ssh <node where Fluo is installed>    # Nodes with Fluo installed is determined by Muchos config
hub clone apache/fluo-examples        # Clone repo of Fluo example applications. Press enter for user/password.
```

Start the example application using its provided scripts.  To show how simple this can be, commands
to run the [WebIndex] application are shown below.  Read the [WebIndex] README to learn more
before running these commands.

```sh
cd fluo-examples/webindex
./bin/webindex init                   # Initialize and start webindex Fluo application
./bin/webindex getpaths 2015-18       # Retrieves CommonCrawl paths file for 2015-18 crawl
./bin/webindex load-s3 2015-18 0-9    # Load 10 files into Fluo in the 0-9 range of 2015-18 crawl
./bin/webindex ui                     # Runs the WebIndex UI
```

If you have your own application to run, you can follow the [Fluo application](fluo-app)
instructions to configure, initialize, and start your application. To automate these steps, you can
mimic the scripts of example Fluo applications above.

## Customize your cluster

After `./bin/muchos setup` is run, users can install additional software on the cluster using their own
Ansible playbooks. In their own playbooks, users can reference any configuration in the Ansible
inventory file at `/etc/ansible/hosts` which is set up by Muchos on the proxy node. The inventory
file lists the hosts for services on the cluster such as the Zookeeper nodes, Namenode, Accumulo
master, etc. It also has variables in the `[all:vars]` section that contain settings that may be
useful in user playbooks. It is recommended that any user-defined Ansible playbooks should be
managed in their own git repository (see [mikewalch/muchos-custom][mc] for an example).

## High-Availability (optional)

Additionally, Muchos can be configured to provide High-Availability for HDFS & Accumulo components. By default,
this feature is off, however it can be turned on by editing the following settings in [muchos.props]
under the `general` section as shown below:

```ini
hdfs_ha = True                        # default is False
nameservice_id = muchoshacluster      # Logical name for the cluster, no special characters
```

Before enabling HA, it is strongly recommended you read the Apache doc for [HDFS HA] & [Accumulo HA]

Also in the `[nodes]` section of [muchos.props] ensure the `journalnode` and `zkfc` service are configured to run.

When `hdfs_ha` is `True` it also enables the ability to have HA resource managers for YARN.  To utilize this feature, specify `resourcemanager` for multiple leader nodes in the `[nodes]` section.

## Terminating your cluster

If you launched your cluster, run the following command to terminate your cluster. WARNING - All
data on your cluster will be lost:

    ./bin/muchos terminate

## Automatic shutdown of clusters

With the default configuration, clusters will not shutdown automatically after a delay and the default
shutdown behavior will be stopping the node.  If you would like your cluster to terminate after 8 hours,
set the following configuration in [muchos.props]:

```ini
shutdown_delay_minutes = 480
shutdown_behavior = terminate
```

If you decide later to cancel the shutdown, run `muchos cancel_shutdown`.

## Retrieving cluster configuration

The `config` command allows you to retrieve cluster configuration for your own scripts:

```sh
$ ./bin/muchos config -p leader.public.ip
10.10.10.10
```

## Contributions

We welcome contributions to the project. [These notes](./CONTRIBUTING.md) should be helpful.

## Powered by

Muchos is powered by the following projects:

 * [boto] - Python library used by `muchos launch` to start a cluster in AWS EC2.
 * [ansible] - Cluster management tool that is used by `muchos setup` to install, configure, and
   start Fluo, Accumulo, Hadoop, etc on an existing EC2 or bare metal cluster.
 * [azure-cli] - The Azure CLI is a command-line tool for managing Azure resources.
 * [ansible-azure] - Ansible includes a suite of modules for interacting with Azure Resource Manager.

[centos7]: https://aws.amazon.com/marketplace/pp/B00O7WM7QW
[aws-config]: http://docs.aws.amazon.com/cli/latest/userguide/cli-config-files.html
[awscli]: https://docs.aws.amazon.com/cli/latest/userguide/installing.html
[awscli-config]: http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#cli-quick-configuration
[azure-cli]: https://docs.microsoft.com/en-us/cli/azure/?view=azure-cli-latest
[ansible-azure]: https://docs.ansible.com/ansible/latest/scenario_guides/guide_azure.html
[fluo-app]: https://github.com/apache/fluo/blob/main/docs/applications.md
[WebIndex]: https://github.com/apache/fluo-examples/tree/main/webindex
[Phrasecount]: https://github.com/apache/fluo-examples/tree/main/phrasecount
[Stresso]: https://github.com/apache/fluo-examples/tree/main/stresso
[boto]: http://boto.cloudhackers.com/en/latest/
[boto3]: https://github.com/boto/boto3
[Ansible]: https://www.ansible.com/
[ci]: https://github.com/apache/fluo-muchos/workflows/CI/badge.svg
[ga]: https://github.com/apache/fluo-muchos/actions
[li]: http://img.shields.io/badge/license-ASL-blue.svg
[ll]: https://github.com/apache/fluo-muchos/blob/main/LICENSE
[logo]: contrib/muchos-logo.png
[mc]: https://github.com/mikewalch/muchos-custom
[fluo]: http://fluo.apache.org/
[accumulo]: http://accumulo.apache.org/
[zookeeper]: http://zookeeper.apache.org/
[hadoop]: http://hadoop.apache.org/
[Uno]: https://github.com/apache/fluo-uno
[muchos.props]: conf/muchos.props.example
[Docker swarm]: https://docs.docker.com/engine/swarm/
[Portainer]: https://github.com/portainer/portainer
[checksums]: conf/checksums
[HDFS HA]: https://hadoop.apache.org/docs/current/hadoop-project-dist/hadoop-hdfs/HDFSHighAvailabilityWithQJM.html
[Accumulo HA]: https://accumulo.apache.org/1.9/accumulo_user_manual.html#_components
[ELK Stack]: https://www.elastic.co/
