# Kinda-p4

Library for emulation of Kubernetes clusters in complex container-based virtual networks. Network topologies can be created with other tools such as Kathara (built-in) or Containernet. Clusters are automatically created using Kind and can be connected to such virtual networks.

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

To use `kinda` CLI add `src/cli` to your path.

## Running

Create a Python script with your topology and cluster, see [examples/nets](examples/nets) for more info, then run it as a root (required to use Kind, iptables, etc...).

## Usage

Kubectl is automatically configured to interact with the cluster. Kubectl traffic is directly passed from the host to the control plane, but any cluster-internal traffic is routed only via the provided virtual network (enscapsulted with GRE).


Internet access can be enabled through any container in a virtualized network; DockerHub access is routed directly through the host and thus doesn't require enabling internet access in the virtualized network itself (meaning you should be able to download docker images).


Library is packed with simple CLI in [src/cli](src/cli) directory, which basically wraps `docker exec -it` so that you can use for example:

`kinda w1 ip a` to print ip config of node named w1

or 

`kinda w1 bash` to run bash there.

## Known Issues

For errors generarated by Kind refer to [their known issues](https://kind.sigs.k8s.io/docs/user/known-issues). Most notably, in case of failure when creating big clusters see (try all of them until the problem is hopefuly solved):
- [inotify reason](https://kind.sigs.k8s.io/docs/user/known-issues/#pod-errors-due-to-too-many-open-files) also see [this thread](https://github.com/kubernetes-sigs/kind/issues/2972)
- [open files reason](https://www.howtogeek.com/805629/too-many-open-files-linux/)
- [docker limitations](https://unix.stackexchange.com/questions/537645/how-to-limit-docker-total-resources)
- [docker out of space](https://unix.stackexchange.com/questions/414483/docker-increase-available-disk-space)


## Debugging

Kubernetes nodes are ubuntu based and come preinstalled with various utilities such as `ping`, `traceroute`, `tcpdump`, `iptables` and `ip` toolkit. To debug deployments usage of node affinity may help, you can assign label to a node by:

`kubectl label node $(kinda reverse <node name>) key=value`

