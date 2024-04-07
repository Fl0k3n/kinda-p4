import os

from Kathara.model.Lab import Lab

import util.containerutils as cutils
from net.KatharaBackedNet import KatharaBackedCluster
from net.util import simple_switch_CLI
from topology.KindaSdnGenerator import KindaSdnTopologyGenerator
from topology.Node import (ExternalDeviceMeta, HostMeta, IncSwitchMeta,
                           K8sNodeMeta)
from topology.Tree import NetworkLink as Link
from topology.Tree import TreeNodeDefinition as Def
from topology.Tree import TreeTopologyBuilder

network = Lab("tree")


def default_inc_switch_meta() -> IncSwitchMeta:
    return IncSwitchMeta(simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 1'))


topo_builder = TreeTopologyBuilder(
    network,
    root_name="external",
    device_definitions=[
        Def("external", ExternalDeviceMeta(default_route_via="r0")),
        Def("r0", default_inc_switch_meta()),
        Def("r1", default_inc_switch_meta()),
        Def("r2", default_inc_switch_meta()),
        Def("r3", default_inc_switch_meta()),
        Def("r4", default_inc_switch_meta()),
        Def("r5", default_inc_switch_meta()),
        Def("r6", default_inc_switch_meta()),
        Def("r7", default_inc_switch_meta()),
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

topo_builder.setup_network()


with KatharaBackedCluster("tree", network) as cluster:
    k8s_nodes = topo_builder.attach_and_build_cluster(cluster)
    KindaSdnTopologyGenerator().write_topology_file(
        funcname="V4_gRpc_topo",
        node_configs=topo_builder.get_devices(),
        k8s_nodes=k8s_nodes,
        path="/home/flok3n/develop/k8s_inc/src/kinda-sdn/generated/v4.go",
    )
    for node in k8s_nodes.values():
        os.system(
            f"kubectl label node {node.internal_node_name} sname={node.name}")
        os.system(
            f"kubectl label node {node.internal_node_name} clustername={node.internal_node_name}")

    cutils.copy_to_container(
        k8s_nodes['c1'].container_id,
        '/home/flok3n/develop/virtual/telemetry2/int-platforms/platforms/bmv2-mininet/int.p4app/utils/int_collector_logging.py',
        '/int_collector_logging.py'
    )
    cutils.docker_exec_detached(
        k8s_nodes['c1'].container_id, 'mkdir', '-p', '/tmp/p4app_logs')

    print('ok')
    # input('press enter to exit')
