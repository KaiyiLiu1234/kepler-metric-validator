#!/bin/bash

# if [ "$#" -ne 1 ]; then
#     echo "1 argument for cpu to generate group for"
#     exit 1
# fi

sudo mkdir /sys/fs/cgroup/isolate_cpu15

echo "isolated" | sudo tee /sys/fs/cgroup/isolate_cpu15/cpuset.cpus.partition

echo "15" | sudo tee /sys/fs/cgroup/isolate_cpu15/cpuset.cpus

echo "0-14" | sudo tee /sys/fs/cgroup/cpuset.cpus