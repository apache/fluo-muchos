![Zetten][logo]
---
[![Build Status][ti]][tl] [![Apache License][li]][ll]

Command-line tool for deploying Fluo or Accumulo to a cluster that can be optionally launched in Amazon EC2.

Installation
------------

First clone the `zetten` repo:

    git clone https://github.com/fluo-io/zetten.git

Now, create and modify your configuration file for zetten:

    cd zetten/
    cp conf/zetten.props.example conf/zetten.props

In order to run `zetten`, your AWS credentials need to be set in `zetten.props` like this:

    [ec2]
    aws.access.key_id=AKIAIOSFODNN7EXAMPLE
    aws.secret.key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

See [AWS Key ID Documentation][2] for more information.

You will need to upload your public key to the AWS management console and set `key.name` in `zetten.props`
to the name of your key pair.  If you want to give others access to your cluster, add their public keys to 
a file named `keys` in your `conf/` directory.  During the setup of your cluster, this file will be appended 
on each node to the `~/.ssh/authorized_keys` file for the user set by the `cluster.username` property.

Launching an EC2 cluster
------------------------

When Zetten launches a cluster, it uses a free CentOS 7 image that is hosted in the AWS marketplace but managed
by the CentOS orginization.  If you have never used this image in EC2 before, you will need to go to the 
[CentOS 7 product page][centos7] to accept the software terms under the 'Manual Launch' tab.  If this is not 
done, you will get an error when you try to launch your cluster.

The CentOS organization periodically updates AMIs and deprecates older AMIs which makes them unavailable to 
new users.  This can also cause an error when you try to launch your cluster.  If this occurs, you will need to
find the AMI ID for your EC2 region on the [CentOS 7 product page][centos7] and set the 'aws_ami' property
in your 'zetten.props' file to override the default AMIs used by Zetten.

Run the following command to launch an EC2 cluster called `mycluster`:

    zetten launch -c mycluster

After your cluster has launched, you do not have to specify a cluster anymore using `-c` (unless you have 
multiple clusters running).

Run the following command to confirm that you can ssh to the leader node:

    zetten ssh

You can check the status of the nodes using the EC2 Dashboard or by running the following command:

    zetten status

Set up the cluster
------------------

The `zetten setup` command will set up your cluster and start Hadoop, Zookeeper, & Accumulo.  It will
download release tarballs of Fluo, Accumulo, Hadoop, etc.  The release versions of these tarballs are 
specified in `zetten.props`.

Optionally, you can have Zetten use a snapshot version (rather than a released version) of Accumulo or Fluo by 
building a snapshot tarball and placing it in the `conf/upload` directory before running `zetten setup`.
This option is only necessary if you want to run the latest unreleased version of Fluo or Accumulo.

```bash
# optional, example commands to build a snapshot version of Fluo
cd /path/to/fluo
mvn package
cp modules/distribution/target/fluo-1.0.0-beta-3-SNAPSHOT-bin.tar.gz /path/to/zetten/conf/upload/
```

The `zetten setup` command will install and start Accumulo, Hadoop, and Zookeeper.  The optional 
services below will only be set up if configured in the [nodes] section of `zetten.props`:

1. `fluo` - Fluo only needs to be installed and configured on a single node in your cluster as Fluo
applications are run in YARN.  If set as a service, `zetten setup` will install and partially configure
Fluo but not start it.  To finish setup, follow the steps in the 'Run a Fluo application' section below.

2. `metrics` - The Metrics service installs and configures collectd, InfluxDB and Grafana.  Cluster metrics
are sent to InfluxDB using collectd and are viewable in Grafana.  If Fluo is running, its metrics will also
be viewable in Grafana.

If you run the `zetten setup` command and a failure occurs, you can run the command again with no issues.
Any cluster setup that was successfully completed will not be repeated.  While some setup steps can take
over a minute, you can use `Ctrl-C` to stop setup if it hangs for a long time.  Just remember to run 
`zetten setup` again to finish setup.

Manage the cluster
------------------

The `setup` command is idempotent.  It can be run again on a working cluster.  It will not change the 
cluster if everything is configured and running correctly.  If a process has stopped, the `setup` 
command will restart the process.

The `zetten wipe` command can be used to wipe all data from the cluster and kill any running processes.
After running the `wipe` command, run the `setup` command to start a fresh cluster.

If you set `proxy_socks_port` in your `zetten.props`, a SOCKS proxy will be created on that port when you
use `zetten ssh` to connect to your cluster.  If you add a proxy managment tool to your browser and
whitelist `http://leader*`, `http://worker*` and `http://metrics*` to redirect traffic to your proxy, you
can view the monitoring & status pages below in your browser. Please note - The hosts in the URLs below match
the configuration in [nodes] of `zetten.prop.example` and may be different for your cluster.

 * NameNode status - [http://leader1:50070/](http://leader1:50070/)
 * ResourceManger status - [http://leader2:8088/cluster](http://leader2:8088/cluster)
 * Accumulo monitor - [http://leader3:50095/](http://leader3:50095/)
 * Spark History Server - [http://leader2:18080/](http://leader2:18080/)
 * Grafana Metrics and Monitoring - [http://metrics:3000/](http://metrics:3000/)

Run a Fluo application
----------------------

If you have a Fluo application to run, follow the steps below to access your Fluo install on the cluster:

```bash
zetten ssh
ssh <node on cluster where Fluo was installed, determined by Zetten config>
cdf   # Alias to change directory to Fluo Home
```

Next, follow the instructions starting at the [Configure a Fluo application][3] section of the Fluo 
production setup instructions to configure, initialize, and start your application.

If you don't have an application, you can run a Fluo example application.  All example applications are listed
and configured in [zetten.props][5].  In general applications are run using the following command:

    zetten run -a <application> [<argument1> <argument2>]

While the application name is required, additional arguments are dependent on the application.  In 
[zetten.props][5], you can find more documentation on how to run each application.

Terminating your EC2 cluster
----------------------------

If you launched your cluster on EC2, run the following command terminate your cluster.  WARNING - All data on
your cluster will be lost:

    zetten terminate

Retrieving cluster configuration
--------------------------------

The `config` command allows you to retrieve cluster configuration for your own scripts:

```bash
$ zetten config -p leader.public.ip
10.10.10.10
```

Powered by
----------

Zetten is powered by the following projects:

 * [boto] - Python library used by `zetten launch` to start a cluster in AWS EC2.
 * [Ansible] - Cluster management tool that is used by `zetten setup` to install, configure, and start Fluo, Accumulo, 
Hadoop, etc on an existing EC2 or bare metal cluster.

Running unit tests
------------------

Install nose using pip:

    pip install nose

The following command runs the unit tests:

    nosetests -w bin/impl

[centos7]: https://aws.amazon.com/marketplace/ordering?productId=b7ee8a69-ee97-4a49-9e68-afaee216db2e
[2]: http://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSGettingStartedGuide/AWSCredentials.html
[3]: https://github.com/fluo-io/fluo/blob/master/docs/prod-fluo-setup.md#configure-a-fluo-application
[4]: https://github.com/fluo-io/fluo-stress
[5]: conf/zetten.props.example
[boto]: http://boto.cloudhackers.com/en/latest/
[Ansible]: https://www.ansible.com/
[ti]: https://travis-ci.org/fluo-io/zetten.svg?branch=master
[tl]: https://travis-ci.org/fluo-io/zetten
[li]: http://img.shields.io/badge/license-ASL-blue.svg
[ll]: https://github.com/fluo-io/fluo/blob/master/LICENSE
[logo]: contrib/zetten-logo.png
