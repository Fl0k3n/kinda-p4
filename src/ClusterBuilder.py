import itertools as it
import os
import subprocess as sp
import tempfile
from concurrent.futures import ThreadPoolExecutor, wait
from typing import IO, NamedTuple

import util.containerutils as containerutils
import util.iputils as iputils
from InternetAccessManager import InternetAccessManager
from K8sNode import ControlNode, K8sNode, WorkerNode
from NodeInitializer import NodeInitializer
from util.iputils import NetIface


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
    KUBECONFIG_PATH = os.path.join(os.environ['HOME'], '.kube', 'config')
    KIND_TIMEOUT_SECONDS = 120
    NODE_INIT_TIMEOUT_SECONDS = 300
    MAX_POOL_SIZE = 32

    def __init__(self, name: str, node_initializer: NodeInitializer, internet_access_mgr: InternetAccessManager) -> None:
        self.name = name
        self.node_initializer = node_initializer
        self.internet_access_mgr = internet_access_mgr
        self.control_nodes: dict[str, ControlNode] = {}
        self.worker_nodes: dict[str, WorkerNode] = {}
        self.internet_access_requested = False
        self.built = False

        self.container_netns = set()
        self.connect_tasks: list[ConnectionTask] = []

    def add_control(self, name: str, with_p4_nic: bool = False):
        self.control_nodes[name] = ControlNode(name, with_p4_nic)

    def add_worker(self, name: str, with_p4_nic: bool = True):
        self.worker_nodes[name] = WorkerNode(name, with_p4_nic)

    def build(self):
        if self.built:
            print("Cluster is already built")
            return

        print('Building cluster...')
        self._run_cluster()

        print("Initializing nodes...")
        self._init_nodes()

        print("Setting up cluster networking...")
        self._setup_connections()
        self._update_cluster_address_translatations()

        if self.internet_access_requested:
            print("Provisioning itnernet access...")
            self.internet_access_mgr.provision_internet_access(
                self.controls + self.workers)

        print("Updating kubectl...")
        self._update_kubectl_cfg()

        self.built = True
        print("Cluster ready")

    def destroy(self):
        if self.internet_access_requested:
            self.internet_access_mgr.teardown_internet_access()

        sp.run(['sudo', 'kind', 'delete', 'clusters', self.name])
        self._clear_attached_namespaces()

    def connect_with_container(self, node_name: str, node_iface: NetIface, container_id: str, container_iface: NetIface,
                               add_default_route_via_container: bool = True):
        assert node_name not in set([x.node_name for x in self.connect_tasks]
                                    ), f'Node {node_name} is already connected to a container'

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

            iputils.connect_namespaces(
                node.netns_name, container_ns, node_iface, bridge_slave_iface)
            iputils.assign_bridge_master(
                container_ns, bridge_slave_iface, container_iface)
            iputils.assign_ipv4(node.netns_name, node_iface)

            if add_default_route_via_container:
                iputils.add_default_route(
                    node.netns_name, container_iface.ipv4)

        self.connect_tasks.clear()

    def _run_cluster(self):
        with tempfile.NamedTemporaryFile() as kind_cfg_file:
            self._prepare_kind_cfg_file(kind_cfg_file)
            kind_sp = sp.Popen(['sudo', 'kind', 'create', 'cluster', '--name', self.name, '--config', kind_cfg_file.name],
                               stdout=sp.PIPE,
                               text=True)
            kind_sp.wait(self.KIND_TIMEOUT_SECONDS)

    def _update_cluster_address_translatations(self):
        for node1, node2 in it.combinations(self.workers + self.controls, 2):
            iputils.add_dnat_rule(
                node1.netns_name, node1.internal_cluster_iface.ipv4,
                node2.internal_cluster_iface.ipv4, node2.net_iface.ipv4)
            iputils.add_dnat_rule(
                node2.netns_name, node2.internal_cluster_iface.ipv4,
                node1.internal_cluster_iface.ipv4, node1.net_iface.ipv4
            )

    def _prepare_kind_cfg_file(self, file: IO[bytes]):
        lines = ([
            'kind: Cluster',
            'apiVersion: kind.x-k8s.io/v1alpha4',
            'nodes:',
            *['- role: control-plane' for _ in self.control_nodes],
            *['- role: worker' for _ in self.worker_nodes],
            ''
        ])

        file.write('\n'.join(lines).encode())
        file.flush()

    def _init_nodes(self):
        self.node_initializer.assing_container_ids(
            self.name, self.workers, self.controls)

        pool_size = min(self.MAX_POOL_SIZE, len(
            self.worker_nodes) + len(self.control_nodes))

        with ThreadPoolExecutor(max_workers=pool_size) as executor:
            control_tasks = [executor.submit(
                self.node_initializer.init_control, control) for control in self.controls]

            worker_tasks = [executor.submit(
                self.node_initializer.init_worker, worker) for worker in self.workers]

            tasks = worker_tasks + control_tasks
            tasks_result = wait(tasks, timeout=self.NODE_INIT_TIMEOUT_SECONDS)

            if tasks_result.not_done:
                print("some tasks didn't finish")
            elif any([task.exception() for task in tasks]):
                print("some tasks finished with an exception")

    def _update_kubectl_cfg(self):
        kubeconfig = sp.run(['sudo', 'kind', 'get', 'kubeconfig',
                            '--name', self.name], capture_output=True, text=True).stdout
        with open(self.KUBECONFIG_PATH, 'w') as f:
            f.write(kubeconfig)

    def _get_node(self, name: str) -> K8sNode:
        return self.worker_nodes.get(name, None) or self.control_nodes[name]

    def _clear_attached_namespaces(self):
        nss_to_remove = [*self.container_netns]

        for node in self.controls + self.workers:
            if node.netns_name is not None:
                nss_to_remove.append(node.netns_name)

        for ns in nss_to_remove:
            sp.run(['sudo', 'ip', 'netns', 'delete', ns])

    def _attach_container_namespace_to_host(self, container_id: str) -> str:
        pid = containerutils.get_container_pid(container_id)
        container_ns = containerutils.create_namespace_name(pid)

        if container_ns not in self.container_netns:
            self.container_netns.add(container_ns)
            containerutils.attach_netns_to_host(pid, container_ns)

        return container_ns

    def _create_bridge_and_get_slave_meta(self, container_ns: str, bridge: NetIface, bridge_to_slaves: dict[BridgeInfo, list[NetIface]]) -> NetIface:
        bridge_info = BridgeInfo(container_ns, bridge.name)

        if bridge_info not in bridge_to_slaves:
            bridge_to_slaves[bridge_info] = []
            iputils.create_bridge(container_ns, bridge)

        bridge_slave_iface = NetIface(
            f'{bridge.name}_slave{len(bridge_to_slaves[bridge_info])}', None, None)
        bridge_to_slaves[bridge_info].append(bridge_slave_iface)

        return bridge_slave_iface

    @property
    def workers(self) -> list[WorkerNode]:
        return list(self.worker_nodes.values())

    @property
    def controls(self) -> list[ControlNode]:
        return list(self.control_nodes.values())
