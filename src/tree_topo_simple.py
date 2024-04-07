import os

from Kathara.model.Lab import Lab

import util.containerutils as cutils
from net.KatharaBackedNet import KatharaBackedCluster
from net.util import execute_simple_switch_cmds, simple_switch_CLI
from topology.KindaSdnGenerator import KindaSdnTopologyGenerator
from topology.Node import (ExternalDeviceMeta, HostMeta, IncSwitchMeta,
                           K8sNodeMeta)
from topology.Tree import NetworkLink as Link
from topology.Tree import TreeNodeDefinition as Def
from topology.Tree import TreeTopologyBuilder

network = Lab("tree")


topology = TreeTopologyBuilder(
    network,
    root_name="r0",
    device_definitions=[
        Def("r0", IncSwitchMeta(
            startup_commands=simple_switch_CLI('mirroring_add 1 1'))),
        Def("r1", IncSwitchMeta(
            startup_commands=simple_switch_CLI('mirroring_add 1 1'))),
        Def("r2", IncSwitchMeta(
            startup_commands=simple_switch_CLI('mirroring_add 1 1'))),
        Def("w1", K8sNodeMeta.Worker()),
        Def("w2", K8sNodeMeta.Worker()),
        Def("w3", K8sNodeMeta.Worker()),
        Def("c1", K8sNodeMeta.Control()),
    ],
    links=[
        Link(("r0", "r1"), ("10.0.1.1/24", "10.0.1.2/24")),
        Link(("r1", "r2"), ("10.0.3.1/24", "10.0.3.2/24")),
        Link(("r0", "w1"), ("10.0.8.1/24", "10.0.8.2/24")),
        Link(("r1", "w2"), ("10.0.9.1/24", "10.0.9.2/24")),
        Link(("r2", "w3"), ("10.0.10.1/24", "10.0.10.2/24")),
        Link(("r2", "c1"), ("10.0.12.1/24", "10.0.12.2/24")),
    ]
)

topology.setup_network()


with KatharaBackedCluster("tree", network) as cluster:
    k8s_nodes = topology.attach_and_build_cluster(cluster)
    KindaSdnTopologyGenerator().write_topology_file(
        funcname="V5_gRpc_topo",
        node_configs=topology.get_devices(),
        k8s_nodes=k8s_nodes,
        path="/home/flok3n/develop/k8s_inc/src/kinda-sdn/generated/v5.go",
    )
    for node in k8s_nodes.values():
        os.system(
            f"kubectl label node {node.internal_node_name} sname={node.name}")
        os.system(
            f"kubectl label node {node.internal_node_name} clustername={node.internal_node_name}")

    cutils.copy_to_container(
        k8s_nodes['w2'].container_id,
        '/home/flok3n/develop/virtual/telemetry2/int-platforms/platforms/bmv2-mininet/int.p4app/utils/int_collector_logging.py',
        '/int_collector_logging.py'
    )
    cutils.docker_exec_detached(
        k8s_nodes['w2'].container_id, 'mkdir', '-p', '/tmp/p4app_logs')

    print('ok')
    # input('press enter to exit')
