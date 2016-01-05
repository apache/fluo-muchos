fluo-deploy
===========

[![Build Status](https://travis-ci.org/fluo-io/fluo-deploy.svg?branch=master)](https://travis-ci.org/fluo-io/fluo-deploy)

Command-line tool for deploying Fluo to a cluster that can be optionally launched in Amazon EC2.

Installation
------------

First clone the `fluo-deploy` repo:
```
git clone https://github.com/fluo-io/fluo-deploy.git
```  

Now, create and modify your configuration file for fluo-deploy:
```
cd fluo-deploy/
cp conf/fluo-deploy.props.example conf/fluo-deploy.props
```

In order to run `fluo-deploy`, your AWS credentials need to be set in `fluo-deploy.props` like this:
```
[ec2]
aws.access.key_id=AKIAIOSFODNN7EXAMPLE
aws.secret.key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

See [AWS Key ID Documentation][2] for more information.

You will need to upload your public key to the AWS management console and set `key.name` in `fluo-deploy.props`
to the name of your key pair.  If you want to give others access to your cluster, add their public keys to 
a file named `keys` in your `conf/` directory.  During the setup of your cluster, this file will be appended 
on each node to the `~/.ssh/authorized_keys` file for the user set by the `cluster.username` property.

Launching an EC2 cluster
------------------------

Run the following command to launch an EC2 cluster called `mycluster`:
```
fluo-deploy launch -c mycluster
```

After your cluster has launched, you do not have to specify a cluster anymore using `-c` (unless you have 
multiple clusters running).

Run the following command to confirm that you can ssh to the leader node:

    fluo-deploy ssh

You can check the status of the nodes using the EC2 Dashboard or by running the following command:

    fluo-deploy status

Set up the cluster
---------------------------

The `fluo-deploy setup` command will set up your cluster and start Hadoop, Zookeeper, & Accumulo.  It will 
download all necessary releases of Fluo, Accumulo, Hadoop, etc.  Optionally, if you want to use a snapshot 
distribution of Accumulo or Fluo, place it in the `conf/upload` directory of fluo-deploy before running 
`'fluo-deploy setup` and it will be uploaded and installed on the cluster.

```bash
cd /path/to/fluo
mvn package
cp modules/distribution/target/fluo-1.0.0-beta-1-SNAPSHOT-bin.tar.gz /path/to/fluo-deploy/conf/upload/
```

The `setup` command installs and configures Fluo but does not start it.  This lets you setup Fluo with any 
observers.  Run the commands below to access your cluster and get to your fluo install:

```bash
fluo-deploy ssh
ssh <FLUO_HOSTNAME>
cdf   # Alias to change directory to Fluo Home
```

Manage the cluster
------------------

The `setup` command is idempotent.  It can be run again on a working cluster.  It will not change the 
cluster if everything is configured and running correctly.  If a process has stopped, the `setup` 
command will restart the process.

The `fluo-deploy wipe` command can be used to wipe all data from the cluster and kill any running processes.
After running the `wipe` command, run the `setup` command to start a fresh cluster.

Run a Fluo application
----------------------

If you have a Fluo application to run, follow the instructions starting at the [Configure a Fluo application][3] 
section of the Fluo production setup instructions to configure, initialize, and start your application.

If you don't have an application, you can run a Fluo example application.  All example applications are listed
and configured in [fluo-deploy.props][5].  In general applications are run using the following command:

    fluo-deploy run -a <application> [<argument1> <argument2>]

While the application name is required, additional arguments are dependent on the application.  In 
[fluo-deploy.props][5], you can find more documentation on how to run each application.

Terminating your EC2 cluster
----------------------------

If you launched your cluster on EC2, run the following command terminate your cluster.  WARNING - All data on
your cluster will be lost:

    fluo-deploy terminate

Retrieving cluster configuration
--------------------------------

The `config` command allows you to retrieve cluster configuration for your own scripts:

```bash
$ fluo-deploy config -p leader.public.ip
10.10.10.10
```

Running unit tests
------------------

Install nose using pip:

    pip install nose

The following command runs the unit tests:

    nosetests -w bin/impl

[2]: http://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSGettingStartedGuide/AWSCredentials.html
[3]: https://github.com/fluo-io/fluo/blob/master/docs/prod-fluo-setup.md#configure-a-fluo-application
[4]: https://github.com/fluo-io/fluo-stress
[5]: conf/fluo-deploy.props.example
