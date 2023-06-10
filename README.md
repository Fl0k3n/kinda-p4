# Kinda-p4

Library for emulation of Kubernetes clusters in complex container-based virtual networks. Network topologies can be created with other tools such as Kathara (built-in) or Containernet. Clusters are automatically created using Kind and can be connected to such a virtual network.

Network topology can be built with a classical networking approach by utilizing, for example, the Quagga project (`kathara/quagga` Docker image) or with a SDN approach using, for example, OpenVSwitch (`kathara/sdn` Docker image) or BMv2 (`kathara/p4` Docker image).

Cluster nodes can be bootstrapped with a BMv2 P4 switch acting as a virtual P4-programmable smart NIC.

Note: All of the pod traffic sent between different Kubernetes nodes is automatically encapsulated with GRE, which may have some consequences for underlying network solutions (for example, if you wanted to use P4 switches and access TCP data, now you would also need to account for the deparsing of the GRE header).

## Requirements
- Linux with ip toolkit, iptables, kubectl and docker (tested on ubuntu with 5.19 kernel)
- Kind 0.18
- Python>=3.10


## Installation

Clone this repo and in the main directory run:

`pip install -r requirements.txt`

## Running

Create a Python script with your topology and cluster, see [examples/nets](examples/nets) for more info, then run it as a root (required to use Kind, iptables, etc...).

## Usage

Kubectl is automatically configured to interact with the cluster. Kubectl traffic is directly passed from the host to the control plane, but any cluster-internal traffic is routed only via the provided virtual network (enscapsulted with GRE).


Internet access can be enabled through any container in a virtualized network; DockerHub access is routed directly through the host and thus doesn't require enabling internet access in the virtualized network itself.
