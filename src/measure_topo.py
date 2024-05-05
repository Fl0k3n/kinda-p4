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
from util.nodenamereplacer import update_node_names_in_files

network = Lab("tree")


topology = TreeTopologyBuilder(
    network,
    root_name="r1",
    device_definitions=[
        Def("r1", IncSwitchMeta(
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 1'))),
        Def("r2", IncSwitchMeta(
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 2'))),
        Def("r3", IncSwitchMeta(
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 4'))),
        Def("w1", K8sNodeMeta.Worker()),
        Def("w2", K8sNodeMeta.Worker()),
        Def("w3", K8sNodeMeta.Worker()),
        Def("w4", K8sNodeMeta.Worker()),
        Def("w5", K8sNodeMeta.Worker()),
        Def("c1", K8sNodeMeta.Control()),
    ],
    links=[
        Link(("r1", "r2"), ("10.0.0.1/24", "10.0.0.2/24")),
        Link(("r2", "r3"), ("10.0.1.1/24", "10.0.1.2/24")),
        Link(("r1", "w1"), ("10.0.2.1/24", "10.0.2.2/24")),
        Link(("r1", "w2"), ("10.0.3.1/24", "10.0.3.2/24")),
        Link(("r3", "w3"), ("10.0.4.1/24", "10.0.4.2/24")),
        Link(("r3", "w4"), ("10.0.5.1/24", "10.0.5.2/24")),
        Link(("r3", "w5"), ("10.0.6.1/24", "10.0.6.2/24")),
        Link(("r3", "c1"), ("10.0.7.1/24", "10.0.7.2/24")),
    ]
)

topology.setup_network()


with KatharaBackedCluster("tree", network) as cluster:
    k8s_nodes = topology.attach_and_build_cluster(cluster)
    KindaSdnTopologyGenerator().write_topology_file(
        funcname="Measure_gRPC_topo",
        rename=True,
        node_configs=topology.get_devices(),
        k8s_nodes=k8s_nodes,
        path="/home/flok3n/develop/k8s_inc/src/kinda-sdn/generated/measure_topo.go",
    )
    for node in k8s_nodes.values():
        os.system(
            f"kubectl label node {node.internal_node_name} sname={node.name}")
        os.system(
            f"kubectl label node {node.internal_node_name} clustername={node.internal_node_name}")

    cutils.copy_to_container(
        k8s_nodes['w5'].container_id,
        '/home/flok3n/develop/virtual/telemetry2/int-platforms/platforms/bmv2-mininet/int.p4app/utils/int_collector_logging.py',
        '/int_collector_logging.py'
    )
    cutils.copy_to_container(
        k8s_nodes['w1'].container_id,
        '/home/flok3n/develop/k8s_inc/src/eval/measure/latency_sender.py',
        '/latency_sender.py'
    )
    cutils.copy_to_container(
        k8s_nodes['w2'].container_id,
        '/home/flok3n/develop/k8s_inc/src/eval/measure/udp_spammer.py',
        '/udp_spammer.py'
    )
    cutils.copy_to_container(
        k8s_nodes['w3'].container_id,
        '/home/flok3n/develop/k8s_inc/src/eval/measure/latency_receiver.py',
        '/latency_receiver.py'
    )
    cutils.copy_to_container(
        k8s_nodes['w4'].container_id,
        '/home/flok3n/develop/k8s_inc/src/eval/measure/udp_spammer_sink.py',
        '/udp_smapper_sink.py'
    )
    cutils.docker_exec_detached(
        k8s_nodes['w5'].container_id, 'mkdir', '-p', '/tmp/p4app_logs')
    update_node_names_in_files(
        k8s_nodes,
        '/home/flok3n/develop/k8s_inc/src/inc-operator/config/example/collector.yaml',
        '/home/flok3n/develop/k8s_inc/src/inc-operator/config/example/eintdepl.yaml'
    )
    print('ok')
    # input('press enter to exit')
