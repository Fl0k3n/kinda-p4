import itertools as it
import tempfile
from concurrent.futures import Future, ThreadPoolExecutor, wait
from typing import Any, Generator, NamedTuple

import util.containerutils as containerutils
import util.iputils as iputils
import util.kindutils as kindutils
from InternetAccessManager import InternetAccessManager
from K8sNode import ControlNode, K8sNode, WorkerNode
from NodeInitializer import NodeInitializer
from util.iputils import Cidr, NetIface
from util.p4 import P4Params


class ConnectionTask(NamedTuple):
    node_name: str
    node_iface: NetIface
    container_id: str
    container_iface: NetIface
    add_default_route_via_container: bool


class BridgeInfo(NamedTuple):
    container_ns: str
    br_name: str


class ClusterBuilder:
    _KIND_TIMEOUT_SECONDS = 120
    _NODE_INIT_TIMEOUT_SECONDS = 300
    _MAX_NODES = 127
    _MAX_POOL_SIZE = 32
    # 10.0-100.0.0 networks are recommended
    _FORBIDDEN_NETWORKS = set([
        Cidr("10.244.0.0", 16),   # reserved for pods
        Cidr("192.168.0.0", 24),  # reserved for tunnels
        Cidr("172.0.0.0", 8)      # reserved for kind and bridges
    ])

    def __init__(self, name: str, node_initializer: NodeInitializer, internet_access_mgr: InternetAccessManager) -> None:
        self.name = name
        self.node_initializer = node_initializer
        self.internet_access_mgr = internet_access_mgr
        self.control_nodes: dict[str, ControlNode] = {}
        self.worker_nodes: dict[str, WorkerNode] = {}
        self.internet_access_requested = False
        self.built = False

        self.container_netns: set[str] = set()
        self.connect_tasks: list[ConnectionTask] = []
        self.tunnel_subnet_generator = self._create_tunnel_subnet_generator()

    @property
    def workers(self) -> list[WorkerNode]:
        return list(self.worker_nodes.values())

    @property
    def controls(self) -> list[ControlNode]:
        return list(self.control_nodes.values())

    def add_control(self, name: str, with_p4_nic: bool = False, p4_params: P4Params = None):
        if with_p4_nic and p4_params is None:
            p4_params = P4Params()

        assert len(self.worker_nodes) + len(self.control_nodes) <= self._MAX_NODES, \
            f'Max nodes count exceeded, ({self._MAX_NODES})'
        self.control_nodes[name] = ControlNode(name, with_p4_nic, p4_params)

    def add_worker(self, name: str, with_p4_nic: bool = False, p4_params: P4Params = None):
        if with_p4_nic and p4_params is None:
            p4_params = P4Params()

        assert len(self.worker_nodes) + len(self.control_nodes) <= self._MAX_NODES, \
            f'Max nodes count exceeded, ({self._MAX_NODES})'
        self.worker_nodes[name] = WorkerNode(name, with_p4_nic, p4_params)

    def build(self):
        if self.built:
            print("Cluster is already built")
            return

        print('Building cluster...')
        self._run_cluster()

        print("Updating kubectl...")
        self._update_kubectl_cfg()

        print("Initializing nodes...")
        self._init_nodes()

        print("Setting up cluster networking...")
        self._setup_connections()
        self._update_cluster_address_translatations()
        self._setup_pod_traffic_tunneling()
        self._setup_p4_nics()

        if self.internet_access_requested:
            print("Provisioning internet access...")
            self.internet_access_mgr.provision_internet_access(
                self.controls + self.workers)

        self.built = True
        print("Cluster ready")

    def destroy(self):
        if self.internet_access_requested:
            self.internet_access_mgr.teardown_internet_access()

        kindutils.delete_cluster(self.name)
        self._clear_attached_namespaces()

    def connect_with_container(self, node_name: str, node_iface: NetIface, container_id: str, container_iface: NetIface,
                               add_default_route_via_container: bool = True):
        assert node_name not in [x.node_name for x in self.connect_tasks], \
            f'Node {node_name} can have at most one connection with virtualized network'
        self._assert_valid(node_iface)
        self._assert_valid(container_iface)

        self.connect_tasks.append(ConnectionTask(
            node_name, node_iface, container_id, container_iface, add_default_route_via_container))

    def enable_internet_access_via(self, container_id: str):
        self.internet_access_mgr.internet_gateway_container_netns = self._attach_container_namespace_to_host(
            container_id)
        self.internet_access_requested = True

    def _setup_connections(self):
        bridge_to_slaves: dict[BridgeInfo, list[NetIface]] = {}

        for node_name, node_iface, container_id, container_iface, add_default_route_via_container in self.connect_tasks:
            node = self._get_node(node_name)
            node.net_iface = node_iface

            container_ns = self._attach_container_namespace_to_host(
                container_id)
            bridge_slave_iface = self._create_bridge_and_get_slave_meta(
                container_ns, container_iface, bridge_to_slaves)

            if node.has_p4_nic:
                iputils.connect_namespaces(
                    node.netns_name, container_ns, node.p4_net_iface, bridge_slave_iface, set_up=True)
                iputils.create_veth_pair(
                    node.netns_name, node.p4_internal_iface, node_iface, set_up=True)
            else:
                iputils.connect_namespaces(
                    node.netns_name, container_ns, node_iface, bridge_slave_iface, set_up=True)

            iputils.assign_bridge_master(
                container_ns, bridge_slave_iface, container_iface)
            iputils.assign_ipv4(node.netns_name, node_iface)

            # checksum offloading leads to invalid TCP checksums which prevent iptables from
            # NATing such packets, making TCP broken in the cluster
            containerutils.turn_off_tcp_checksum_offloading(
                node.container_id, node.net_iface.name)

            if add_default_route_via_container:
                iputils.add_default_route(
                    node.netns_name, container_iface.ipv4)

        self.connect_tasks.clear()

    def _setup_pod_traffic_tunneling(self):
        node_nums = {node.name: idx for idx,
                     node in enumerate(self.controls + self.workers)}

        for node1, node2 in it.combinations(self.workers + self.controls, 2):
            tun1, tun2 = self._create_tunnel_meta(node1, node2, node_nums)
            for src, dst, tun in [(node1, node2, tun1), (node2, node1, tun2)]:
                iputils.create_gre_tunnel(
                    src.netns_name, tun, src.net_iface.ipv4, dst.net_iface.ipv4, set_up=True)

                for pod_cidr in dst.pod_cidrs:
                    # TODO drop that requirement, although it shouldn't be a problem in practice
                    assert pod_cidr.netmask == 24, f'Only /24 pod cidrs are supported, got {pod_cidr.netmask}'

                    # Kind quite successfully manages to assure that route to pod cidr via node.internal_cluster_interface
                    # exists, so we can't simply delete it and put a different route, what we can do instead is add
                    # two equivalent, but more specific routes that will be preferred in the routing process
                    subnet1, subnet2 = self._get_tunnel_target_routes(
                        pod_cidr.ipv4)
                    iputils.add_route(
                        src.netns_name, f'{subnet1}/25', tun.ipv4)
                    iputils.add_route(
                        src.netns_name, f'{subnet2}/25', tun.ipv4)

    def _run_cluster(self):
        with tempfile.NamedTemporaryFile() as kind_cfg_file:
            kindutils.prepare_kind_cfg_file(kind_cfg_file, len(
                self.control_nodes), len(self.worker_nodes))
            kindutils.run_cluster(
                self.name, kind_cfg_file.name, self._KIND_TIMEOUT_SECONDS)

    def _update_cluster_address_translatations(self):
        for node1, node2 in it.permutations(self.workers + self.controls, 2):
            iputils.add_dnat_rule(
                node1.netns_name, node1.internal_cluster_iface.ipv4,
                node2.internal_cluster_iface.ipv4, node2.net_iface.ipv4)

    def _init_nodes(self):
        self.node_initializer.setup_node_info()
        self.node_initializer.assing_container_ids(
            self.name, self.workers, self.controls)

        pool_size = min(self._MAX_POOL_SIZE, len(self.controls + self.workers))

        with ThreadPoolExecutor(max_workers=pool_size) as executor:
            control_tasks = [executor.submit(
                self.node_initializer.init_control, control) for control in self.controls]

            worker_tasks = [executor.submit(
                self.node_initializer.init_worker, worker) for worker in self.workers]

            self._await_tasks(worker_tasks + control_tasks,
                              self._NODE_INIT_TIMEOUT_SECONDS)

    def _update_kubectl_cfg(self):
        kindutils.update_kubectl_cfg(self.name, kindutils.KUBECONFIG_PATH)

    def _get_node(self, name: str) -> K8sNode:
        return self.worker_nodes.get(name, None) or self.control_nodes[name]

    def _clear_attached_namespaces(self):
        nss_to_remove = [*self.container_netns]

        for node in self.controls + self.workers:
            if node.netns_name is not None:
                nss_to_remove.append(node.netns_name)

        for ns in nss_to_remove:
            iputils.delete_namespace(iputils.HOST_NS, ns)

    def _attach_container_namespace_to_host(self, container_id: str) -> str:
        pid = containerutils.get_container_pid(container_id)
        container_ns = containerutils.create_namespace_name(pid)

        if container_ns not in self.container_netns:
            self.container_netns.add(container_ns)
            containerutils.attach_netns_to_host(pid, container_ns)

        return container_ns

    def _create_bridge_and_get_slave_meta(self, container_ns: str, bridge: NetIface,
                                          bridge_to_slaves: dict[BridgeInfo, list[NetIface]]) -> NetIface:
        bridge_info = BridgeInfo(container_ns, bridge.name)

        if bridge_info not in bridge_to_slaves:
            bridge_to_slaves[bridge_info] = []
            iputils.create_bridge(container_ns, bridge)

        bridge_slave_iface = NetIface(
            f'{bridge.name}_slave{len(bridge_to_slaves[bridge_info])}', None, None)
        bridge_to_slaves[bridge_info].append(bridge_slave_iface)

        return bridge_slave_iface

    def _create_tunnel_meta(self, n1: K8sNode, n2: K8sNode, node_enumerations: dict[str, int]) -> tuple[NetIface, NetIface]:
        d_num = node_enumerations[n2.name]
        s_num = node_enumerations[n1.name]
        last_subnet_byte = next(self.tunnel_subnet_generator)

        tun1 = NetIface(f'tgre_{d_num}',
                        f'192.168.0.{last_subnet_byte}', 31)
        tun2 = NetIface(f'tgre_{s_num}',
                        f'192.168.0.{last_subnet_byte + 1}', 31)
        return tun1, tun2

    def _get_tunnel_target_routes(self, ipv4: str) -> tuple[str, str]:
        route_parts = ipv4.split('.')
        return '.'.join([*route_parts[:3], '0']), '.'.join([*route_parts[:3], '128'])

    def _setup_p4_nics(self):
        p4_nodes = [node for node in self.controls +
                    self.workers if node.has_p4_nic and node.p4_params.run_nic]
        if p4_nodes:
            with ThreadPoolExecutor(max_workers=min(self._MAX_POOL_SIZE, len(p4_nodes))) as executor:
                tasks = [executor.submit(
                    self.node_initializer.run_p4_nic, node) for node in p4_nodes]

                try:
                    self._await_tasks(tasks, self._NODE_INIT_TIMEOUT_SECONDS)
                except Exception as e:
                    print('Failed to setup p4 NICs')
                    print(e)

    def _await_tasks(self, tasks: list[Future[Any]], timeout: float = None):
        tasks_result = wait(tasks, timeout=timeout)

        if tasks_result.not_done:
            raise Exception("some tasks didn't finish")

        if failed_tasks := [task for task in tasks if task.exception() is not None]:
            print("some tasks finished with an exception")
            raise failed_tasks[0].exception()

    def _assert_valid(self, iface: NetIface):
        iface_net_parts = iface.ipv4.split('.')
        for net in self._FORBIDDEN_NETWORKS:
            net_parts = net.ipv4.split('.')[:net.netmask // 8 + 1]
            assert '.'.join(iface_net_parts[:len(net_parts)]) != '.'.join(net_parts), \
                f'Network {iface.ipv4} is forbidden, pick other one not in {self._FORBIDDEN_NETWORKS}'

    def _create_tunnel_subnet_generator(self) -> Generator[int, None, None]:
        for i in range(0, 253, 2):
            yield i
