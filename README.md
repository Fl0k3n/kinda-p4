# Kinda-p4


Tool for integrating Kubernetes clusters built with Kind with virtualized local networks provided by container-based tools such as Kathara or Containernet. Cluster nodes can be bootstrapped with a BMV2 P4 switch acting as a virtual P4 NIC.

## Requirements
- Linux with ip toolkit
- Kind and its requirements such as Docker and iptables
- Python>=3.10


## Installation

`pip install -r requirements.txt`

## Running

Create a Python script and build your topology and cluster, see examples for reference, then run it as a root (required to use Kind, iptables, etc...).

## Usage

Kubectl is automatically configured to interact with the cluster; see [examples/k8s] (examples/k8s) for reference. Kubectl traffic is directly passed from the host to the control plane, but any cluster-internal traffic is routed only via the provided virtual network.


Internet access can be enabled through any container in a virtualized network; DockerHub access is routed directly through the host and thus doesn't require enabling internet access in the virtualized network itself.
