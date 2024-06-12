
from Kathara.model.Lab import Lab

from net.KatharaBackedNet import KatharaBackedCluster
from net.util import simple_switch_CLI
from topology.KindaSdnGenerator import KindaSdnTopologyGenerator
from topology.Node import (FORWARD_PROGRAM, TELEMETRY_PROGRAM, IncSwitchMeta,
                           K8sNodeMeta)
from topology.Tree import NetworkLink as Link
from topology.Tree import TreeNodeDefinition as Def
from topology.Tree import TreeTopologyBuilder
from util.containerutils import copy_to_container
from util.iputils import TrafficControlInfo
from util.nodenamereplacer import update_node_names_in_files

network = Lab("tree")

rate_limit_kbps = 8000
inc_switch_rate_limit_cmds = [
    f'set_queue_rate {rate_limit_kbps // 8}', 'set_queue_depth 100']

NODE_MTU = 1100

topology = TreeTopologyBuilder(
    network,
    root_name="r1",
    device_definitions=[
        Def("r1", IncSwitchMeta(
            program=TELEMETRY_PROGRAM,
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 1', *inc_switch_rate_limit_cmds))),
        Def("r2", IncSwitchMeta(
            program=FORWARD_PROGRAM,
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 1', *inc_switch_rate_limit_cmds))),
        Def("r3", IncSwitchMeta(
            program=TELEMETRY_PROGRAM,
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 1', *inc_switch_rate_limit_cmds))),
        Def("r4", IncSwitchMeta(
            program=FORWARD_PROGRAM,
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 1', *inc_switch_rate_limit_cmds))),
        Def("r5", IncSwitchMeta(
            program=TELEMETRY_PROGRAM,
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 1', *inc_switch_rate_limit_cmds))),
        Def("r6", IncSwitchMeta(
            program=FORWARD_PROGRAM,
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 1', *inc_switch_rate_limit_cmds))),
        Def("r7", IncSwitchMeta(
            program=TELEMETRY_PROGRAM,
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 1', *inc_switch_rate_limit_cmds))),
        Def("r8", IncSwitchMeta(
            program=FORWARD_PROGRAM,
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 1', *inc_switch_rate_limit_cmds))),
        Def("r9", IncSwitchMeta(
            program=TELEMETRY_PROGRAM,
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 1', *inc_switch_rate_limit_cmds))),
        Def("r10", IncSwitchMeta(
            program=FORWARD_PROGRAM,
            simple_switch_cli_commands=simple_switch_CLI('mirroring_add 1 1', *inc_switch_rate_limit_cmds))),
        Def("w1", K8sNodeMeta.Worker(mtu=NODE_MTU)),
        Def("w2", K8sNodeMeta.Worker(mtu=NODE_MTU)),
        Def("w3", K8sNodeMeta.Worker(mtu=NODE_MTU)),
        Def("w4", K8sNodeMeta.Worker(mtu=NODE_MTU)),
        Def("w5", K8sNodeMeta.Worker(mtu=NODE_MTU)),
        Def("w6", K8sNodeMeta.Worker(mtu=NODE_MTU)),
        Def("w7", K8sNodeMeta.Worker(mtu=NODE_MTU)),
        Def("w8", K8sNodeMeta.Worker(mtu=NODE_MTU)),
        Def("w9", K8sNodeMeta.Worker(mtu=NODE_MTU)),
        Def("w10", K8sNodeMeta.Worker(mtu=NODE_MTU)),
        Def("w11", K8sNodeMeta.Worker(mtu=NODE_MTU)),
        Def("w12", K8sNodeMeta.Worker(mtu=NODE_MTU)),
        Def("c1", K8sNodeMeta.Control()),
    ],
    links=[
        Link(("r1", "r7"), ("10.0.13.1/24", "10.0.13.2/24")),
        Link(("r2", "r7"), ("10.0.14.1/24", "10.0.14.2/24")),
        Link(("r3", "r8"), ("10.0.15.1/24", "10.0.15.2/24")),
        Link(("r4", "r8"), ("10.0.16.1/24", "10.0.16.2/24")),
        Link(("r5", "r9"), ("10.0.17.1/24", "10.0.17.2/24")),
        Link(("r6", "r9"), ("10.0.18.1/24", "10.0.18.2/24")),
        Link(("r7", "r10"), ("10.0.19.1/24", "10.0.19.2/24")),
        Link(("r8", "r10"), ("10.0.20.1/24", "10.0.20.2/24")),
        Link(("r9", "r10"), ("10.0.21.1/24", "10.0.21.2/24")),

        Link(("r1", "w1"), ("10.0.0.1/24", "10.0.0.2/24")),
        Link(("r1", "w2"), ("10.0.1.1/24", "10.0.1.2/24")),
        Link(("r2", "w3"), ("10.0.2.1/24", "10.0.2.2/24")),
        Link(("r2", "w4"), ("10.0.3.1/24", "10.0.3.2/24")),
        Link(("r3", "w5"), ("10.0.4.1/24", "10.0.4.2/24")),
        Link(("r3", "w6"), ("10.0.5.1/24", "10.0.5.2/24")),
        Link(("r4", "c1"), ("10.0.6.1/24", "10.0.6.2/24")),
        Link(("r4", "w7"), ("10.0.7.1/24", "10.0.7.2/24")),
        Link(("r4", "w8"), ("10.0.8.1/24", "10.0.8.2/24")),
        Link(("r5", "w9"), ("10.0.9.1/24", "10.0.9.2/24")),
        Link(("r5", "w10"), ("10.0.10.1/24", "10.0.10.2/24")),
        Link(("r6", "w11"), ("10.0.11.1/24", "10.0.11.2/24")),
        Link(("r6", "w12"), ("10.0.12.1/24", "10.0.12.2/24")),
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
    update_node_names_in_files(
        k8s_nodes,
        '/home/flok3n/develop/k8s_inc/src/inc-operator/config/example/collector.yaml',
        '/home/flok3n/develop/k8s_inc/src/inc-operator/config/example/intdepl_http.yaml',
        '/home/flok3n/develop/k8s_inc/src/inc-operator/config/example/intdepl_udp.yaml'
    )
    # if receiver is scheduled on w9 then one of senders should be on w10 and vice versa
    for n in ['w3', 'w9', 'w10']:
        copy_to_container(
            k8s_nodes[n].container_id,
            '/home/flok3n/develop/k8s_inc_analysis/iperf_tcp_increasing.sh',
            'iperf_tcp_increasing.sh'
        )
        copy_to_container(
            k8s_nodes[n].container_id,
            '/home/flok3n/develop/k8s_inc_analysis/iperf_tcp_constant.sh',
            'iperf_tcp_constant.sh'
        )
        copy_to_container(
            k8s_nodes[n].container_id,
            '/home/flok3n/develop/k8s_inc_analysis/iperf_udp_increasing.sh',
            'iperf_udp_inc.sh'
        )
        copy_to_container(
            k8s_nodes[n].container_id,
            '/home/flok3n/develop/k8s_inc_analysis/iperf_udp_constant.sh',
            'iperf_udp_const.sh'
        )
    for n in ['w8', 'w11']:
        copy_to_container(
            k8s_nodes[n].container_id,
            '/home/flok3n/develop/k8s_inc_analysis/iperf_s.sh',
            'iperf_s.sh'
        )
    print('ok')
    # input('press enter to exit')
