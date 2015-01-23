fluo-deploy
========

Scripts used to run a Fluo cluster on EC2

Installation
------------

First clone the `fluo-deploy` repo:
```
git clone https://github.com/fluo-io/fluo-deploy.git
```

In order to run `fluo-deploy`, your AWS credentials need to be set at `~/.aws/credentials` in a file like this:
```
[default]
aws_access_key_id=AKIAIOSFODNN7EXAMPLE
aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

This file can be created by [installing the AWS client][1] and running the following command:
```
aws configure
```
See [AWS getting started guide][2] for more information.

Now, create and modify your configuration file for fluo-deploy:
```
cd fluo-deploy/
cp conf/fluo-deploy.props.example conf/fluo-deploy.props
```

You will need upload your public key to the AWS management console and set `key.name` in `fluo-deploy.props`
to the name of your key pair.

Launching an EC2 cluster
------------------------

Run the following command to launch an EC2 cluster called `mycluster`:
```
fluo-deploy launch mycluster
```

After your cluster has launched, run the following command to confirm that you can ssh to the leader node:
```
fluo-deploy ssh mycluster
```

You can check the status of the nodes using the EC2 Dashboard or by running the following command:
```
fluo-deploy status mycluster
```

Set up Fluo on your cluster
---------------------------

If you are setting up Fluo on a cluster that was not created using the `launch` command, you will need to 
create a hosts file in `conf/hosts` that is named after you cluster (see `conf/hosts/example_cluster` for an example).

Before running the next command, you will need to build a Fluo distribution and copy it to `cluster/tarballs/` directory of
fluo-deploy:
```
cd /path/to/fluo
mvn package
cp modules/distribution/target/fluo-1.0.0-beta-1-SNAPSHOT-bin.tar.gz /path/to/fluo-deploy/cluster/tarballs/
```

Run the following command to set up your cluster and run Hadoop, Zookeeper, & Accumulo:
```
fluo-deploy setup mycluster
```

The `setup` command can be run again if you cluster becomes unstable or if you want to change Accumulo or Hadoop 
configuration found in `templates/conf`.  The `setup` command installs and configures Fluo but does not start it.
This lets you setup Fluo with any observers.  Run the commands below to access your Fluo install:
```
fluo-deploy ssh mycluster
ssh <FLUO_HOSTNAME>
cdf   # Alias to change directory to Fluo Home
```

When Fluo is configured with your observers, run the following commands to initialize and start Fluo:
```
fluo init
fluo yarn start
```

Terminating your EC2 cluster
----------------------------

If you launched your cluster on EC2, run the following command terminate your cluster.  WARNING - All data on
your cluster will be lost:
```
fluo-deploy terminate mycluster
```

Running unit tests
------------------

Install nose using pip:
```
pip install nose
```

Run the following commands to run the tests:
```
cd bin/impl
nosetests
```

[1]: http://docs.aws.amazon.com/cli/latest/userguide/installing.html
[2]: http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html
