![Muchos][logo]
---
[![Build Status][ti]][tl] [![Apache License][li]][ll]

**Muchos automates setting up [Apache Accumulo][accumulo] or [Apache Fluo][fluo] (and their dependencies) on a cluster**

Muchos makes it easy to launch a cluster in Amazon's EC2 and deploy Accumulo or Fluo to it. Muchos
enables developers to experiment with Accumulo or Fluo in a realistic, distributed environment.
Muchos installs all software using tarball distributions which makes its easy to experiment
with the latest versions of Accumulo, Hadoop, Zookeeper, etc without waiting for downstream packaging.

Muchos is not recommended at this time for production environments as it has no support for updating
and upgrading dependencies. It also has a wipe command that is great for testing but dangerous for
production environments.

Muchos is structured into two high level components:

 * [Ansible] scripts that install and configure Fluo and its dependencies on a cluster.
 * Python scripts that push the Ansible scripts from a local development machine to a cluster and
   run them. These Python scripts can also optionally launch a cluster in EC2 using [boto].

Checkout [Uno] for setting up Accumulo or Fluo on a single machine.

## Installation

First clone the Muchos repo:

    git clone https://github.com/astralway/muchos.git

Now, create and modify your configuration file for Muchos:

    cd muchos/
    cp conf/muchos.props.example conf/muchos.props

In order to run the `muchos` command, you will need to create [AWS configuration and credential files][aws-config]
in your home directory. These files can be created by hand or by running `aws configure` using the [AWS CLI][aws-cli].

You will need to upload your public key to the AWS management console and set `key.name` in
`muchos.props` to the name of your key pair.  If you want to give others access to your cluster, add
their public keys to a file named `keys` in your `conf/` directory.  During the setup of your
cluster, this file will be appended on each node to the `~/.ssh/authorized_keys` file for the user
set by the `cluster.username` property.

## Launching an EC2 cluster

When Muchos launches a cluster, it uses a free CentOS 7 image that is hosted in the AWS marketplace
but managed by the CentOS organization. If you have never used this image in EC2 before, you will
need to go to the [CentOS 7 product page][centos7] to accept the software terms under the 'Manual
Launch' tab. If this is not done, you will get an error when you try to launch your cluster.

The CentOS organization periodically updates AMIs and deprecates older AMIs which makes them
unavailable to new users.  This can also cause an error when you try to launch your cluster. If
this occurs, you will need to find the AMI ID for your EC2 region on the
[CentOS 7 product page][centos7] and set the 'aws_ami' property in your 'muchos.props' file to
override the default AMIs used by Muchos.

Run the following command to launch an EC2 cluster called `mycluster`:

    muchos launch -c mycluster

After your cluster has launched, you do not have to specify a cluster anymore using `-c` (unless you
have multiple clusters running).

Run the following command to confirm that you can ssh to the leader node:

    muchos ssh

You can check the status of the nodes using the EC2 Dashboard or by running the following command:

    muchos status

## Set up the cluster

The `muchos setup` command will set up your cluster and start Hadoop, Zookeeper, & Accumulo.  It
will download release tarballs of Fluo, Accumulo, Hadoop, etc. The versions of these tarballs are
specified in `muchos.props` and can be changed if desired.

Optionally, Muchos can setup the cluster using an Accumulo or Fluo tarball that is placed in the
`conf/upload` directory of Muchos. This option is only necessary if you want to use an unreleased
version of Fluo or Accumulo. Before running the `muchos setup` command, you should confirm that the
version and SHA-256 hash of your tarball matches what is set in `conf/muchos.props`. Run the command
`shasum -a 256 /path/to/tarball` on your tarball to determine its hash.

The `muchos setup` command will install and start Accumulo, Hadoop, and Zookeeper.  The optional 
services below will only be set up if configured in the [nodes] section of `muchos.props`:

1. `fluo` - Fluo only needs to be installed and configured on a single node in your cluster as Fluo
applications are run in YARN.  If set as a service, `muchos setup` will install and partially
configure Fluo but not start it.  To finish setup, follow the steps in the 'Run a Fluo application'
section below.

2. `metrics` - The Metrics service installs and configures collectd, InfluxDB and Grafana.  Cluster
metrics are sent to InfluxDB using collectd and are viewable in Grafana.  If Fluo is running, its
metrics will also be viewable in Grafana.

3. `mesosmaster` - If specified, a Mesos master will be started on this node and Mesos slaves will
be started on all workers nodes. The Mesos status page will be viewable at
`http://<MESOS_MASTER_NODE>:5050/`. Marathon will also be started on this node and will be viewable
at `http://<MESOS_MASTER_NODE>:8080/`.

If you run the `muchos setup` command and a failure occurs, you can repeat the command until setup
completes. Any work that was successfully completed will not be repeated. While some setup steps can
take over a minute, use `ctrl-c` to stop setup if it hangs for a long time. Just remember to run
`muchos setup` again to finish setup.

## Manage the cluster

The `setup` command is idempotent. It can be run again on a working cluster. It will not change the
cluster if everything is configured and running correctly. If a process has stopped, the `setup` 
command will restart the process.

The `muchos wipe` command can be used to wipe all data from the cluster and kill any running
processes. After running the `wipe` command, run the `setup` command to start a fresh cluster.

If you set `proxy_socks_port` in your `muchos.props`, a SOCKS proxy will be created on that port
when you use `muchos ssh` to connect to your cluster. If you add a proxy management tool to your
browser and whitelist `http://leader*`, `http://worker*` and `http://metrics*` to redirect traffic
to your proxy, you can view the monitoring & status pages below in your browser. Please note - The
hosts in the URLs below match the configuration in [nodes] of `muchos.prop.example` and may be
different for your cluster.

 * NameNode status - [http://leader1:50070/](http://leader1:50070/)
 * ResourceManger status - [http://leader2:8088/cluster](http://leader2:8088/cluster)
 * Accumulo monitor - [http://leader3:50095/](http://leader3:50095/)
 * Spark History Server - [http://leader2:18080/](http://leader2:18080/)
 * Grafana Metrics and Monitoring - [http://metrics:3000/](http://metrics:3000/)
 * Mesos status - [http://leader1:5050/](http://leader1:5050/) (if `mesosmaster` configured on leader1)
 * Marathon status - [http://leader1:8080/](http://leader1:8080/) (if `mesosmaster` configured on leader1)

## Run a Fluo application

Running an example Fluo application like [WebIndex], [Phrasecount], or [Stresso] is easy
with Muchos as it configures your shell with common environment variables. To run an example
application, SSH to a node on cluster where Fluo is installed and clone the example repo:

```bash
muchos ssh                            # SSH to cluster proxy node                    
ssh <node where Fluo is installed>    # Nodes with Fluo installed is determined by Muchos config
hub clone astralway/webindex          # Clone repo of example application.  Press enter for user/password.
```

Start the example application using its provided scripts.  To show how simple this can be, commands
to run the [WebIndex] application are shown below.  Read the [WebIndex] README to learn more
before running these commands.

```bash
cd webindex/      
./bin/webindex init                   # Initialize and start webindex Fluo application
./bin/webindex getpaths 2015-18       # Retrieves CommonCrawl paths file for 2015-18 crawl
./bin/webindex load-s3 2015-18 0-9    # Load 10 files into Fluo in the 0-9 range of 2015-18 crawl
./bin/webindex ui                     # Runs the WebIndex UI
```

If you have your own application to run, you can follow the [Fluo application](fluo-app)
instructions to configure, initialize, and start your application. To automate these steps, you can
mimic the scripts of example Fluo applications above.

## Customize your cluster

After `muchos setup` is run, users can install additional software on the cluster using their own
Ansible playbooks. In their own playbooks, users can reference any configuration in the Ansible
inventory file at `/etc/ansible/hosts` which is set up by Muchos on the proxy node. The inventory
file lists the hosts for services on the cluster such as the Zookeeper nodes, Namenode, Accumulo
master, etc. It also has variables in the `[all:vars]` section that contain settings that may be
useful in user playbooks. It is recommended that any user-defined Ansible playbooks should be
managed in their own git repository (see [mikewalch/muchos-custom][mc] for an example).

## Terminating your EC2 cluster

If you launched your cluster on EC2, run the following command terminate your cluster. WARNING - All
data on your cluster will be lost:

    muchos terminate

## Automatic shutdown of EC2 clusters

With the default configuration, EC2 clusters will not shutdown automatically after a delay and the default
shutdown behavior will be stopping the node.  If you would like your cluster to terminate after 8 hours,
set the following configuration in `muchos.props`:

```
shutdown_delay_minutes = 480
shutdown_behavior = terminate
```

If you decide later to cancel the shutdown, run `muchos cancel_shutdown`.

## Retrieving cluster configuration

The `config` command allows you to retrieve cluster configuration for your own scripts:

```bash
$ muchos config -p leader.public.ip
10.10.10.10
```

## Powered by

Muchos is powered by the following projects:

 * [boto] - Python library used by `muchos launch` to start a cluster in AWS EC2.
 * [Ansible] - Cluster management tool that is used by `muchos setup` to install, configure, and
   start Fluo, Accumulo, Hadoop, etc on an existing EC2 or bare metal cluster.

## Muchos Testing

Muchos has unit tests.  To run them, first install nose using pip:

    pip install nose

The following command runs the unit tests:

    nosetests -w lib/

[centos7]: https://aws.amazon.com/marketplace/ordering?productId=b7ee8a69-ee97-4a49-9e68-afaee216db2e
[aws-config]: http://docs.aws.amazon.com/cli/latest/userguide/cli-config-files.html
[aws-cli]: http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#cli-quick-configuration
[fluo-app]: https://github.com/apache/fluo/blob/master/docs/applications.md
[WebIndex]: https://github.com/astralway/webindex
[Phrasecount]: https://github.com/astralway/phrasecount
[Stresso]: https://github.com/astralway/stresso
[boto]: http://boto.cloudhackers.com/en/latest/
[Ansible]: https://www.ansible.com/
[ti]: https://travis-ci.org/astralway/muchos.svg?branch=master
[tl]: https://travis-ci.org/astralway/muchos
[li]: http://img.shields.io/badge/license-ASL-blue.svg
[ll]: https://github.com/astralway/muchos/blob/master/LICENSE
[logo]: contrib/muchos-logo.png
[mc]: https://github.com/mikewalch/muchos-custom
[fluo]: http://fluo.apache.org/
[accumulo]: http://accumulo.apache.org/
[zookeeper]: http://zookeeper.apache.org/
[hadoop]: http://hadoop.apache.org/
[Uno]: https://github.com/astralway/uno
