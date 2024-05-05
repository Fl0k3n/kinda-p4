from collections import deque
from dataclasses import dataclass
from typing import Generator, Optional

from Kathara.model.Lab import Lab as KatharaLab
from Kathara.model.Machine import Machine as KataharaMachine

from core.ClusterBuilder import ClusterBuilder, NetIface
from core.K8sNode import K8sNode
from net.util import (container_id, execute_simple_switch_cmds,
                      run_in_kathara_machine)
from topology.Builder import TopologyBuilder
from topology.Node import (LinkConfig, NodeConfig, NodeMeta, NodeType,
                           PeerNameToIpMac)
from util.containerutils import docker_exec_detached
from util.iputils import Cidr, TrafficControlInfo, get_subnet
from util.logger import logger
from util.macs import mac_generator


class TreeNode:
    def __init__(self, name: str, meta: NodeMeta, connection_ip_macs: PeerNameToIpMac,
                 parent: Optional["TreeNode"] = None, children: list["TreeNode"] = None) -> None:
        self.name = name
        self.meta = meta
        self.parent = parent
        self.children = children if children is not None else []
        self.connection_ip_macs = connection_ip_macs


@dataclass
class NetworkLink:
    names: tuple[str, str]
    addrs: tuple[str, str]


@dataclass
class TreeNodeDefinition:
    name: str
    meta: NodeMeta


class TreeTopologyBuilder(TopologyBuilder):
    '''
    Builder of strongly connected topology with no cycles. Any (except K8s) node can be a root,
    it's not treated differently but is designated for easier debugging. 

    K8s nodes must be leaves and must have single connection to the cluster.
    '''

    def __init__(self, network: KatharaLab, root_name: str,
                 device_definitions: list[TreeNodeDefinition],
                 links: list[NetworkLink], node_traffic_control: TrafficControlInfo = None) -> None:
        self.root = self._make_tree(root_name, device_definitions, links)
        self.nodes = self._build_node_dict()
        self.network = network
        self.node_traffic_control = node_traffic_control

    def setup_network(self):
        kathara_bridges = self._kathara_bridge_gen()
        link_to_bridge: dict[tuple[str, str], str] = {}

        for node in self._iter_nodes_bfs():
            node_type = node.meta.get_type()
            if node_type == NodeType.K8S:
                assert not node.children, 'K8s node must be a leaf'
                continue

            machine = self.network.get_or_new_machine(node.name)
            self._set_machine_meta(node, machine)

            if node.parent is not None:
                parent_bridge = link_to_bridge[(node.parent.name, node.name)]
                self.network.connect_machine_to_link(node.name, parent_bridge)

            for child in node.children:
                if child.meta.get_type() != NodeType.K8S:
                    bridge = next(kathara_bridges)
                    self.network.connect_machine_to_link(node.name, bridge)
                    link_to_bridge[(node.name, child.name)] = bridge

    def attach_and_build_cluster(self, cluster: ClusterBuilder) -> dict[str, K8sNode]:
        k8s_nodes = self._connect_cluster_nodes(cluster)
        cluster.build()
        self._run_after_cluster_built_actions()
        return k8s_nodes

    def kathara_machines(self, *names: list[str]) -> list[KataharaMachine]:
        return [self.network.get_machine(name) for name in names]

    def get_devices(self) -> list[NodeConfig]:
        res = []
        for node in self._iter_nodes_bfs():
            neighs: list[TreeNode] = []
            if node.parent is not None:
                neighs.append(node.parent)
            neighs.extend(node.children)
            links = []
            for n in neighs:
                ip, mac = node.connection_ip_macs[n.name]
                links.append(LinkConfig(
                    peer_name=n.name, masked_ip=ip, mac=mac))
            res.append(NodeConfig(name=node.name, meta=node.meta, links=links))
        return res

    def _build_node_dict(self) -> dict[str, TreeNode]:
        return {
            node.name: node for node in self._iter_nodes_bfs()
        }

    def _set_machine_meta(self, node: TreeNode, machine: KataharaMachine):
        node_type = node.meta.get_type()
        if node_type == NodeType.HOST or node_type == NodeType.EXTERNAL:
            meta = node.meta.simple_host_meta()
            machine.update_meta(args={
                "image": meta.image,
                "exec_commands": meta.startup_commands,
            })
        elif node_type == NodeType.INC_SWITCH:
            meta = node.meta.inc_switch_meta()
            meta_args = {
                "image": meta.image,
                "bridged": meta.open_grpc,
            }
            if meta.open_grpc:
                meta_args['ports'] = [
                    f'{meta.grpc_port}:{meta.grpc_internal_port}']
            if meta.startup_commands:
                meta_args['exec_commands'] = meta.startup_commands
            machine.update_meta(args=meta_args)
        else:
            raise Exception(f"Unexpected node type {node_type}")

    def _get_host_link_commands(self, node: TreeNode, link_idx: int, node_name: str, mtu: int = None) -> list[str]:
        ip, mac = node.connection_ip_macs[node_name]
        iface_name = f'eth{link_idx}'
        res = [
            f'ifconfig {iface_name} {ip} up',
            f'ip link set {iface_name} address {mac}',
            f'ethtool -K {iface_name} rx off tx off'
        ]
        if mtu is not None:
            res.append(f'ip link set dev {iface_name} mtu {mtu}')
        return res

    def _connect_cluster_nodes(self, cluster: ClusterBuilder) -> dict[str, K8sNode]:
        k8s_nodes = {}
        for node in self._iter_nodes_bfs():
            if node.meta.get_type() != NodeType.K8S:
                continue
            meta = node.meta.k8s_meta()
            if meta.control_plane:
                k8s_nodes[node.name] = cluster.add_control(node.name)
            else:
                k8s_nodes[node.name] = cluster.add_worker(node.name)

            parent = node.parent

            node_iface_name = 'eth0k'
            node_ip, node_mac = node.connection_ip_macs[parent.name]
            node_ip, node_mask = node_ip.split('/')

            parent_iface_name = self._get_parent_iface_name_to_k8s_node(node)
            parent_ip, parent_mac = parent.connection_ip_macs[node.name]
            parent_ip, parent_mask = parent_ip.split('/')

            cluster.connect_with_container(
                node.name,
                node_iface=NetIface(node_iface_name, ipv4=node_ip,
                                    netmask=int(node_mask), mac=node_mac,
                                    egress_traffic_control=self.node_traffic_control),
                container_id=container_id(parent.name, self.network.name),
                container_iface=NetIface(
                    parent_iface_name, ipv4=parent_ip,
                    netmask=int(parent_mask), mac=parent_mac,
                    egress_traffic_control=self.node_traffic_control)
            )
        return k8s_nodes

    def _get_parent_iface_name_to_k8s_node(self, k8s_node: TreeNode) -> str:
        parent = k8s_node.parent
        non_k8s_ifaces = len(
            [x for x in parent.children if x.meta.get_type() != NodeType.K8S])
        if parent.parent is not None:
            non_k8s_ifaces += 1
        if parent.meta.get_type() == NodeType.INC_SWITCH:
            if parent.meta.inc_switch_meta().open_grpc:
                non_k8s_ifaces += 1

        k8s_nodes_count = 0
        for child in parent.children:
            if child.name == k8s_node.name:
                return f'eth{non_k8s_ifaces + k8s_nodes_count}'
            if child.meta.get_type() == NodeType.K8S:
                k8s_nodes_count += 1

        raise Exception('Invalid tree state')

    def _iter_nodes_bfs(self) -> Generator[TreeNode, None, None]:
        queue = deque[TreeNode]()
        queue.append(self.root)
        while queue:
            cur = queue.popleft()
            yield cur
            queue.extend(cur.children)

    def _run_after_cluster_built_actions(self):
        # at this point all interfaces are setup and we can configure them
        self._configure_interfaces()
        self._execute_simple_switch_CLI_commands()
        # in these devices routing should be fully p4-based, don't let OS get in the way
        self._delete_OS_routes_in_inc_switches()

    def _execute_simple_switch_CLI_commands(self):
        for node in self._iter_nodes_bfs():
            if node.meta.get_type() == NodeType.INC_SWITCH and node.meta.inc_switch_meta().simple_switch_cli_commands is not None:
                docker_exec_detached(container_id(
                    node.name, self.network.name), './s.sh')

    def _delete_OS_routes_in_inc_switches(self):
        for node in self._iter_nodes_bfs():
            if node.meta.get_type() == NodeType.INC_SWITCH:
                for (masked_ip, _) in node.connection_ip_macs.values():
                    ip, mask = masked_ip.split('/')
                    network_ip = get_subnet(
                        Cidr(ipv4=ip, netmask=int(mask))).masked_ip
                    run_in_kathara_machine(self.network.get_machine(node.name), [
                        f'ip route del {network_ip}',
                    ], self.network.name)

    def _configure_interfaces(self):
        for node in self._iter_nodes_bfs():
            node_type = node.meta.get_type()
            if node_type == NodeType.K8S:
                continue
            commands = self._build_configure_interfaces_commands(node)
            if commands:
                run_in_kathara_machine(node.name, commands, self.network.name)

    def _build_configure_interfaces_commands(self, node: TreeNode) -> list[str]:
        commands = []
        node_type = node.meta.get_type()
        if node_type == NodeType.HOST or node_type == NodeType.EXTERNAL:
            meta = node.meta.simple_host_meta()
            prev_ifaces = 0
            if node.parent is not None:
                commands.extend(self._get_host_link_commands(
                    node, 0, node.parent.name, meta.mtu))
                prev_ifaces = 1
            for i, child in enumerate(node.children):
                commands.extend(self._get_host_link_commands(
                    node, i + prev_ifaces, child.name, meta.mtu))
            if meta.default_route_via is not None:
                peer = self.nodes[meta.default_route_via]
                peer_ip, _ = peer.connection_ip_macs[node.name]
                commands.append(
                    f'ip route add default via {self._without_mask(peer_ip)}')
        elif node_type == NodeType.INC_SWITCH:
            meta = node.meta.inc_switch_meta()
            neighs: list[TreeNode] = []
            if node.parent is not None:
                neighs.append(node.parent)
            neighs.extend(node.children)
            run_iface_names = [""] * len(neighs)

            counter = 0
            for i, neigh in enumerate(neighs):
                if neigh.meta.get_type() != NodeType.K8S:
                    commands.extend(self._get_host_link_commands(
                        node, counter, neigh.name))
                    run_iface_names[i] = f'eth{counter}'
                    counter += 1

            if meta.open_grpc:
                counter += 1

            for i, neigh in enumerate(neighs):
                if neigh.meta.get_type() == NodeType.K8S:
                    commands.extend(self._get_host_link_commands(
                        node, counter, neigh.name))
                    run_iface_names[i] = f'eth{counter}'
                    counter += 1
            commands.append(meta.get_run_command(run_iface_names))
        return commands

    def _kathara_bridge_gen(self):
        cur = 0
        while True:
            yield f'KB{cur}'
            cur += 1

    def _without_mask(self, ip: str) -> str:
        return ip.split("/")[0] if "/" in ip else ip

    def _make_tree(self, root_name: str, defs: list[TreeNodeDefinition], links: list[NetworkLink]) -> TreeNode:
        mac_gen = mac_generator()
        used_defs = [False] * len(defs)

        name_to_def = {x.name: x for x in defs}
        name_to_idx = {x.name: idx for idx, x in enumerate(defs)}

        def get_links(name: str) -> list[NetworkLink]:
            res = []
            for link in links:
                if name == link.names[0]:
                    res.append(link)
                elif name == link.names[1]:
                    res.append(NetworkLink(
                        (link.names[1], link.names[0]), (link.addrs[1], link.addrs[0])))
            return res

        queue = deque[tuple[TreeNodeDefinition, TreeNode]]()
        queue.append((name_to_def[root_name], None))
        used_defs[name_to_idx[root_name]] = True
        root = None

        while queue:
            cur, parent = queue.popleft()

            neigh_links = get_links(cur.name)
            cur_node = TreeNode(cur.name, cur.meta, {
                x.names[1]: (x.addrs[0], next(mac_gen)) for x in neigh_links
            }, parent)

            if parent is None:
                root = cur_node
            else:
                parent.children.append(cur_node)

            for neigh in neigh_links:
                neigh_idx = name_to_idx[neigh.names[1]]
                if not used_defs[neigh_idx]:
                    used_defs[neigh_idx] = True
                    queue.append((defs[neigh_idx], cur_node))

        assert root is not None

        if unused := [d for d, used in zip(defs, used_defs) if not used]:
            for d in unused:
                logger.error(f'device is defined but not connected: {d}')
            assert False

        return root
