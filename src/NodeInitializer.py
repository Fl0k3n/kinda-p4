import itertools as it
import os
import subprocess as sp

import util.containerutils as containerutils
import util.iputils as iputils
from K8sNode import ControlNode, K8sNode, WorkerNode

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.join(_THIS_DIR, 'scripts')


class NodeInitializer:
    _KIND_IFACE_NAME = 'eth0'
    _NODE_INIT_SCRIPT_FILENAME = 'node_init.sh'
    _BMV2_FILENAME = 'bmv2_install.sh'
    _NODE_INIT_PATH = os.path.join(_SCRIPTS_DIR, _NODE_INIT_SCRIPT_FILENAME)
    _BMV2_PATH = os.path.join(_SCRIPTS_DIR, _BMV2_FILENAME)
    _HOSTNAMES_TO_ROUTE_VIA_HOST = [
        'registry-1.docker.io', 'production.cloudflare.docker.com']

    def __init__(self) -> None:
        self.ips_to_route_via_host = self._resolve_hostnames()

    def assing_container_ids(self, cluster_name: str, workers: list[WorkerNode], controls: list[ControlNode]):
        docker_output = sp.run(['sudo', 'docker', 'ps'],
                               capture_output=True, text=True)
        workers_iter = iter(workers)
        controls_iter = iter(controls)

        for line in docker_output.stdout.splitlines():
            if cluster_name in line:
                node = next(workers_iter) if 'worker' in line else next(
                    controls_iter)
                node.container_id = line.split()[0]

        assert next(workers_iter, None) is None and next(controls_iter, None) is None, \
            'Failed to assign container ids to some nodes'

    def init_worker(self, node: WorkerNode):
        print(f'Initializing worker: {node.name}')
        self._init_node(node)
        print(f'worker: {node.name} ready')

    def init_control(self, node: ControlNode):
        print(f'Initializing control plane node: {node.name}')
        self._init_node(node)
        print(f'control plane node: {node.name} ready')

    def _init_node(self, node: K8sNode):
        self._init_container_requirements(node)
        node.internal_cluster_iface = iputils.get_interface_info(
            node.netns_name, self._KIND_IFACE_NAME)

        if node.has_p4_nic:
            self._install_bmv2(node)

        host_ip = iputils.get_host_ipv4_in_network_with(
            node.internal_cluster_iface.ipv4, node.internal_cluster_iface.netmask)

        for ip in self.ips_to_route_via_host:
            iputils.add_route(node.netns_name, ip, host_ip)

    def _init_container_requirements(self, node: K8sNode):
        containerutils.copy_and_run_script_in_container(
            node.container_id, self._NODE_INIT_PATH, f'/home/{self._NODE_INIT_SCRIPT_FILENAME}')

        node.pid = containerutils.get_container_pid(node.container_id)
        node.netns_name = f'ns_{node.name}'
        containerutils.attach_netns_to_host(node.pid, node.netns_name)

    def _install_bmv2(self, node: K8sNode):
        containerutils.copy_and_run_script_in_container(
            node.container_id, self._BMV2_PATH, f'/home/{self._BMV2_FILENAME}')
        print(f'Installed bmv2 on: {node.name}')

    def _resolve_hostnames(self) -> list[str]:
        return list(it.chain(*map(iputils.resolve_hostnames_to_ipv4, self._HOSTNAMES_TO_ROUTE_VIA_HOST)))
