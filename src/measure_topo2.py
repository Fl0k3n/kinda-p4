import os

from Kathara.model.Lab import Lab

import util.containerutils as cutils
from net.KatharaBackedNet import KatharaBackedCluster
from net.util import simple_switch_CLI
from topology.KindaSdnGenerator import KindaSdnTopologyGenerator
from topology.Node import (FORWARD_PROGRAM, TELEMETRY_PROGRAM,
                           ExternalDeviceMeta, HostMeta, IncSwitchMeta,
                           K8sNodeMeta)
from topology.Tree import NetworkLink as Link
from topology.Tree import TreeNodeDefinition as Def
from topology.Tree import TreeTopologyBuilder
from util.iputils import TrafficControlInfo
from util.nodenamereplacer import update_node_names_in_files

network = Lab("tree")

rate_limit_kbps = 800
inc_switch_rate_limit_cmds = [
    f'set_queue_rate {rate_limit_kbps // 8}', 'set_queue_depth 100']

topology = TreeTopologyBuilder(
    network,
    root_name="r1",
    device_definitions=[
        Def("r1", IncSwitchMeta(
            program=FORWARD_PROGRAM,
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 1', *inc_switch_rate_limit_cmds))),
        Def("r2", IncSwitchMeta(
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 2', *inc_switch_rate_limit_cmds))),
        Def("r3", IncSwitchMeta(
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 4', *inc_switch_rate_limit_cmds))),
        Def("w1", K8sNodeMeta.Worker()),
        Def("w2", K8sNodeMeta.Worker()),
        Def("c1", K8sNodeMeta.Control()),
    ],
    links=[
        Link(("r1", "r2"), ("10.0.0.1/24", "10.0.0.2/24")),
        Link(("r2", "r3"), ("10.0.1.1/24", "10.0.1.2/24")),
        Link(("r1", "w1"), ("10.0.2.1/24", "10.0.2.2/24")),
        Link(("r3", "w2"), ("10.0.4.1/24", "10.0.4.2/24")),
        Link(("r3", "c1"), ("10.0.7.1/24", "10.0.7.2/24")),
    ],
    node_traffic_control=TrafficControlInfo(
        latency_ms=10, rate_kbitps=rate_limit_kbps, burst_kbitps=rate_limit_kbps)
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
    cutils.copy_to_container(
        k8s_nodes['w1'].container_id,
        '/home/flok3n/develop/k8s_inc/src/eval/measure/latency_sender.py',
        '/latency_sender.py'
    )
    cutils.copy_to_container(
        k8s_nodes['w2'].container_id,
        '/home/flok3n/develop/k8s_inc/src/eval/measure/latency_receiver.py',
        '/latency_receiver.py'
    )
    print('ok')
    # input('press enter to exit')
