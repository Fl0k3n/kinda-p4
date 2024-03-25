from Kathara.model.Lab import Lab

from net.KatharaBackedNet import KatharaBackedCluster
from topology.KindaSdnGenerator import KindaSdnTopologyGenerator
from topology.Node import (ExternalDeviceMeta, HostMeta, IncSwitchMeta,
                           K8sNodeMeta)
from topology.Tree import NetworkLink as Link
from topology.Tree import TreeNodeDefinition as Def
from topology.Tree import TreeTopologyBuilder

network = Lab("tree")

topology = TreeTopologyBuilder(
    network,
    root_name="external",
    device_definitions=[
        Def("external", ExternalDeviceMeta(default_route_via="r0")),
        Def("r0", IncSwitchMeta()),
        Def("r1", IncSwitchMeta()),
        Def("r2", IncSwitchMeta()),
        Def("r3", IncSwitchMeta()),
        Def("r4", IncSwitchMeta()),
        Def("r5", IncSwitchMeta()),
        Def("r6", IncSwitchMeta()),
        Def("r7", IncSwitchMeta()),
        Def("w1", K8sNodeMeta.Worker()),
        Def("w2", K8sNodeMeta.Worker()),
        Def("w3", K8sNodeMeta.Worker()),
        Def("w4", K8sNodeMeta.Worker()),
        Def("c1", K8sNodeMeta.Control()),
    ],
    links=[
        Link(("external", "r0"), ("10.0.0.1/24", "10.0.0.2/24")),
        Link(("r0", "r1"), ("10.0.1.1/24", "10.0.1.2/24")),
        Link(("r0", "r2"), ("10.0.2.1/24", "10.0.2.2/24")),
        Link(("r0", "r3"), ("10.0.3.1/24", "10.0.3.2/24")),
        Link(("r0", "r4"), ("10.0.4.1/24", "10.0.4.2/24")),
        Link(("r1", "r5"), ("10.0.5.1/24", "10.0.5.2/24")),
        Link(("r2", "r6"), ("10.0.6.1/24", "10.0.6.2/24")),
        Link(("r3", "r7"), ("10.0.7.1/24", "10.0.7.2/24")),
        Link(("r4", "c1"), ("10.0.8.1/24", "10.0.8.2/24")),
        Link(("r5", "w1"), ("10.0.9.1/24", "10.0.9.2/24")),
        Link(("r5", "w2"), ("10.0.10.1/24", "10.0.10.2/24")),
        Link(("r6", "w3"), ("10.0.11.1/24", "10.0.11.2/24")),
        Link(("r7", "w4"), ("10.0.12.1/24", "10.0.12.2/24")),
    ]
)

topology.setup_network()

KindaSdnTopologyGenerator().write_topology_file(
    funcname="V4_gRpc_topo",
    node_configs=topology.get_devices(),
    path="/home/flok3n/develop/k8s_inc/src/kinda-sdn/generated/v4.go",
)

with KatharaBackedCluster("tree", network) as cluster:
    k8s_nodes = topology.attach_and_build_cluster(cluster)
    print('ok')
