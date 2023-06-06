import os
import subprocess as sp
import tempfile
from concurrent.futures import ThreadPoolExecutor, wait
from typing import IO
from uuid import uuid4

import containerutils
import iputils
from ControlNode import ControlNode
from K8sNode import K8sNode
from NodeInitializer import NodeInitializer
from WorkerNode import WorkerNode


class ClusterBuilder:
    KUBECONFIG_PATH = os.path.join(os.environ['HOME'], '.kube', 'config')
    KIND_TIMEOUT_SECONDS = 120
    NODE_INIT_TIMEOUT_SECONDS = 300
    MAX_POOL_SIZE = 32

    def __init__(self, name: str, node_initializer: NodeInitializer = None) -> None:
        self.name = name
        self.control_nodes: dict[str, ControlNode] = {}
        self.worker_nodes: dict[str, WorkerNode] = {}
        self.node_initializer = node_initializer if node_initializer is not None else NodeInitializer()

        self.container_netns = []

    def add_control(self, name: str, ipv4: str, netmask: int):
        self.control_nodes[name] = ControlNode(name, ipv4, netmask)

    def add_worker(self, name: str, ipv4: str, netmask: int, with_p4_nic: bool = True):
        self.worker_nodes[name] = WorkerNode(name, ipv4, netmask, with_p4_nic)

    def build(self):
        print('Building cluster...')
        with tempfile.NamedTemporaryFile() as kind_cfg_file:
            self._prepare_kind_cfg_file(kind_cfg_file)
            self._run_cluster(kind_cfg_file.name)

        print("Initializing nodes...")
        self._init_nodes()

        self._update_kubectl_cfg()
        print('Cluster ready')

    def destroy(self):
        sp.run(['sudo', 'kind', 'delete', 'clusters', self.name])

        nss_to_remove = [*self.container_netns]

        for node in [*self.control_nodes.values(), *self.worker_nodes.values()]:
            if node.netns_name is not None:
                nss_to_remove.append(node.netns_name)

        for ns in nss_to_remove:
            sp.run(['sudo', 'ip', 'netns', 'delete', ns])

    def connect_with_container(self, node_name: str, container_id: str, container_ipv4: str,
                               add_default_route_via_container: bool = True):
        node = self.worker_nodes.get(
            node_name, None) or self.control_nodes[node_name]
        pid = containerutils.get_container_pid(container_id)
        container_ns = f'ns_{pid}'
        container_iface = 'eth1634'  # TODO
        self.container_netns.append(container_ns)

        containerutils.attach_netns_to_host(pid, container_ns)
        iputils.connect_namespaces(
            node.netns_name, container_ns, node.net_iface, container_iface)

        iputils.assign_ipv4(node.netns_name, node.net_iface,
                            node.ipv4, node.netmask)
        iputils.assign_ipv4(container_ns, container_iface,
                            container_ipv4, node.netmask)

        if add_default_route_via_container:
            iputils.add_default_route(node.netns_name, container_ipv4)

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

    def _run_cluster(self, cfg_file_path: str):
        kind_sp = sp.Popen(
            ['sudo', 'kind', 'create', 'cluster', '--name',
                self.name, '--config', cfg_file_path],
            stdout=sp.PIPE,
            text=True)

        kind_sp.wait(self.KIND_TIMEOUT_SECONDS)

    def _init_nodes(self):
        self.node_initializer.assing_container_ids(self.name,
                                                   list(
                                                       self.worker_nodes.values()),
                                                   list(self.control_nodes.values()))

        pool_size = min(self.MAX_POOL_SIZE, len(
            self.worker_nodes) + len(self.control_nodes))

        with ThreadPoolExecutor(max_workers=pool_size) as executor:
            control_tasks = [executor.submit(self.node_initializer.init_control, control)
                             for control in self.control_nodes.values()]

            worker_tasks = [executor.submit(self.node_initializer.init_worker, worker)
                            for worker in self.worker_nodes.values()]

            tasks_result = wait([*worker_tasks, *control_tasks],
                                timeout=self.NODE_INIT_TIMEOUT_SECONDS)

            if tasks_result.not_done:
                print('some tasks failed')  # TODO

    def _update_kubectl_cfg(self):
        kubeconfig = sp.run(['sudo', 'kind', 'get', 'kubeconfig',
                            '--name', self.name], capture_output=True, text=True).stdout
        with open(self.KUBECONFIG_PATH, 'w') as f:
            f.write(kubeconfig)
