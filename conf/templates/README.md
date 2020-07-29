## Muchos EC2 Cluster Templates

Cluster templates are intended to provide greater flexibility, if needed,
with respect to instance type selection and launch configuration for
your EC2 hosts. For example, cluster templates may be ideal for use
cases that require distinct, per-host launch configurations, and
for use cases that require hosts to have persistent, EBS-backed data
volumes (rather than ephemeral volumes, the muchos default for EC2
clusters).

If you are already familiar with muchos and with the basics of EC2
launch requests, then creating your own launch templates will be simple
and straightforward.

Please follow the guidance provided here to ensure compatibility between
your custom templates and muchos automation.

## Configuration

### Select a cluster template in *muchos.props*

```ini
[ec2]
...
cluster_template = example
...
```

The configured value must match the name of a subdirectory under
`conf/templates`

```sh
~$ ls -1 fluo-muchos/conf/templates/example
devices
metrics.json
namenode.json
resourcemanager.json
zookeeper.json
worker.json
```

The subdirectory will contain one or more user-defined EC2 launch
templates `*.json` for your various host service types, and it will
include a `devices` file specifying the desired mount points for all
data volumes (excluding root volumes, as they are mounted
automatically).

### Defining EC2 launch templates and device mounts for your hosts

#### Launch Templates: `{service-name}.json` files

Each JSON file represents a standard EC2 launch request, and each file
name must match one of the predefined muchos service names, as
defined in the **nodes** section of *muchos.props*. E.g.,

```ini
...
[nodes]
leader1 = namenode,resourcemanager,accumulomaster
leader2 = metrics,zookeeper
worker1 = worker
worker2 = worker
worker3 = worker
worker4 = worker
```

In template mode, the first service listed for a given host denotes the
template to be selected for its launch.

Based on the example given above:
* **leader1** selects `namenode.json`
* **leader2** selects `metrics.json`
* **worker1** selects `worker.json`
* and so on...

For example, `namenode.json` might be defined as follows...

```json
{
  "KeyName": "${key_name}",
  "BlockDeviceMappings": [
    {
      "DeviceName": "/dev/sda1",        # Here, /dev/sda1 denotes the root volume
      "Ebs": {
        "DeleteOnTermination": true,
        "VolumeSize": 40,
        "VolumeType": "gp2"
      }
    },
    {
      "DeviceName": "/dev/sdf",          # Here, /dev/sdf (a.k.a "/dev/xvdf") denotes
      "Ebs": {                           # our single EBS-backed data volume
        "DeleteOnTermination": true,
        "VolumeSize": 500,
        "VolumeType": "gp2"
      }
    }
  ],
  "ImageId": "${aws_ami}",
  "InstanceType": "m4.4xlarge",
  "NetworkInterfaces": [
    {
      "DeviceIndex": 0,
      "AssociatePublicIpAddress": "${associate_public_ip}",
      "Groups": [
        "${security_group_id}"
      ]
    }
  ],
  "EbsOptimized": true,
  "InstanceInitiatedShutdownBehavior": "${shutdown_behavior}"
}
```

#### Property Placeholders

The `${property name}` placeholders demonstrated above are optional and
are intended to simplify template creation and reduce maintenance burden.
They allow any matching properties from the **ec2** section of `muchos.props`
to be interpolated automatically.

If needed, you may also define your own custom properties and have them be injected
automatically by simply adding them to the **ec2** section of
`muchos.props` and to your templates

#### Device Mounts: `devices` file

The `devices` file contains the user-defined mapping of storage
devices and mount points for all data (i.e., non-root) volumes in your
cluster. Muchos Ansible scripts leverage this information to prepare
all data volumes during the cluster `setup` phase.

Two (and only two) device mappings should exist within `devices`:
* One map to represent your **worker** device mounts, and
* One map to represent the device mounts on all other hosts, i.e., the
  **default** map

For example, the `devices` file below specifies 4 mount points for all
`worker` instance types, and specifies 1 mount point for all
other hosts via the `default` map.

```json
{
  "default": {
    "mounts": [
      "/data0"       # For non-workers, mount the /data0 directory
    ],               # on /dev/xvdf (a.k.a "/dev/sdf")
    "devices": [
      "/dev/xvdf"
    ]
  },
  "worker": {
    "mounts": [
      "/data0",
      "/data1",
      "/data2",
      "/data3"       # For workers, mount the /data0 directory on
    ],               # /dev/xvdf (a.k.a "/dev/sdf"), mount /data1 on
    "devices": [     # /dev/xvdg (a.k.a "/dev/sdg"), and so on...
      "/dev/xvdf",
      "/dev/xvdg",
      "/dev/xvdh",
      "/dev/xvdi"
    ]
  }
}
```

Naturally, you should take care to ensure that your **BlockDeviceMappings**
also align to *default* vs *worker* node type semantics. As you
explore the example files, you should observe the implicit link betweeen
a data volume denoted by `BlockDeviceMappings[N].DeviceName` and its
respective device map entry in the `devices` file.

* **Note**: While *DeviceName* mount profiles should not vary among
  your default (non-worker) nodes, other attributes within *BlockDeviceMappings*,
  such as *DeleteOnTermination*, *VolumeSize*, *etc*, may vary as needed
* **Note**: Be aware that the device names used by AWS EC2 launch requests
  may differ from the actual names assigned by the EC2 block device driver, which
  can be confusing. Please read
  [this](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/device_naming.html)
  and [also this](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/block-device-mapping-concepts.html)
  for additional information and guidance, if needed
* **Note**: Root EBS volumes may be configured as desired in your JSON
  launch templates, but only non-root, "data" storage devices should be
  specified in `devices`, as root devices are mounted automatically

## Beyond the Launch Phase: *Setup*, *Terminate*, *Etc*

Aside from the configuration differences described above, which impact
the `launch` phase, all other muchos operations behave the same in
template mode as in default mode.

