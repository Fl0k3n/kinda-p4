from Kathara.model.Lab import Lab

from net.KatharaBackedNet import KatharaBackedCluster
from topology.Node import (ExternalDeviceMeta, IncSwitchMeta, K8sNodeMeta,
                           NetDeviceMeta)
from topology.Tree import NetworkLink as Link
from topology.Tree import TreeNodeDefinition as Def
from topology.Tree import TreeTopologyBuilder

network = Lab("tree")
builder = TreeTopologyBuilder(
    network,
    root_name="internet",
    device_definitions=[
        Def("internet", ExternalDeviceMeta()),                 # ubuntu-based host
        Def("gateway", NetDeviceMeta(image="kathara/quagga")), # quagga router
        Def("r1", IncSwitchMeta()),                            # p4 programmable switch
        Def("r2", IncSwitchMeta()),
        Def("w1", K8sNodeMeta.Worker()),                       # Kubernetes worker node  
        Def("w2", K8sNodeMeta.Worker()),
        Def("w3", K8sNodeMeta.Worker()),
        Def("c1", K8sNodeMeta.Control())],                     # Kubernetes control plane node  
    links=[
        Link(("internet", "gateway"), ("10.0.1.1/24", "10.0.1.2/24")),
        Link(("gateway", "r1"), ("10.0.2.1/24", "10.0.2.2/24")),
        Link(("gateway", "r2"), ("10.0.3.1/24", "10.0.3.2/24")),
        Link(("r1", "w1"), ("10.0.4.1/24", "10.0.4.2/24")),
        Link(("r1", "w2"), ("10.0.5.1/24", "10.0.5.2/24")),
        Link(("r2", "w3"), ("10.0.6.1/24", "10.0.6.2/24")),
        Link(("r2", "c1"), ("10.0.7.1/24", "10.0.7.2/24"))]
)
builder.setup_network()
with KatharaBackedCluster("example-cluster", network) as cluster:
    builder.attach_and_build_cluster(cluster)
 