import itertools as it
import os
from time import sleep

import util.containerutils as containerutils
import util.iputils as iputils
import util.kubectlutils as kubectlutils
from core.K8sNode import ControlNode, K8sNode, WorkerNode
from util.iputils import NetIface
from util.kubectlutils import NodesInfo
from util.p4 import P4Params

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.join(_THIS_DIR, '..', 'scripts')


class NodeInitializer:
    _KIND_IFACE_NAME = 'eth0'
    _NODE_INIT_SCRIPT_FILENAME = 'node_init.sh'
    _BMV2_FILENAME = 'bmv2_install.sh'
    _NODE_INIT_PATH = os.path.join(_SCRIPTS_DIR, _NODE_INIT_SCRIPT_FILENAME)
    _BMV2_PATH = os.path.join(_SCRIPTS_DIR, _BMV2_FILENAME)
    _BMV2_EXECUTABLE = 'simple_switch'  # use 'simple_switch_grpc' instead?
    _WAIT_FOR_BMV2_INIT_SECONDS = 1
    _HOSTNAMES_TO_ROUTE_VIA_HOST = [
        'registry-1.docker.io', 'production.cloudflare.docker.com']

    def __init__(self) -> None:
        self.ips_to_route_via_host = self._resolve_hostnames()
        self.nodes_info: NodesInfo = None

    def assing_container_ids(self, cluster_name: str, workers: list[WorkerNode], controls: list[ControlNode]):
        docker_ps_output = containerutils.docker_ps()
        workers_iter = iter(workers)
        controls_iter = iter(controls)

        for line in docker_ps_output.splitlines():
            node = None
            if f'{cluster_name}-control-plane' in line:
                node = next(controls_iter)
            elif f'{cluster_name}-worker' in line:
                node = next(workers_iter)

            if node is not None:
                node.container_id = line.split()[0]

        assert next(workers_iter, None) is None and next(controls_iter, None) is None, \
            f'Failed to assign container ids to some nodes, docker output is:\n {docker_ps_output}'

    def setup_node_info(self):
        self.nodes_info = kubectlutils.get_nodes_info()

    def init_worker(self, node: WorkerNode):
        print(f'Initializing worker: {node.name}')
        self._init_node(node)
        print(f'worker: {node.name} ready')

    def init_control(self, node: ControlNode):
        print(f'Initializing control plane node: {node.name}')
        self._init_node(node)
        print(f'control plane node: {node.name} ready')

    def run_p4_nic(self, node: K8sNode):
        self._assert_p4_can_be_run_on(node)
        print(f'Starting P4 NIC on {node.name}')
        params = node.p4_params

        args = [self._BMV2_EXECUTABLE, '-i',
                f'0@{node.p4_net_iface.name}', '-i', f'1@{node.p4_internal_iface.name}']
        if params.host_script_path is not None:
            args.append(self._get_p4_script_container_path(params))
        else:
            args.append('--no-p4')

        containerutils.docker_exec_detached(node.container_id, *args)
        sleep(self._WAIT_FOR_BMV2_INIT_SECONDS)
        if containerutils.is_process_running(node.container_id, self._BMV2_EXECUTABLE):
            print(f'P4 NIC is running on {node.name}')
        else:
            print(f'Failed to run P4 NIC on {node.name}')

    def _init_node(self, node: K8sNode):
        self._init_container_requirements(node)
        self._init_kubernetes_internals(node)

        if node.has_p4_nic:
            self._install_bmv2(node)
            self._setup_p4_iface_meta(node)
            self._handle_p4_params(node)

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

    def _init_kubernetes_internals(self, node: K8sNode):
        node.internal_cluster_iface = iputils.get_interface_info(
            node.netns_name, self._KIND_IFACE_NAME)
        node.internal_node_meta = kubectlutils.get_info_of_node_with_internal_ip(
            self.nodes_info, node.internal_cluster_iface.ipv4)
        node.internal_node_name = kubectlutils.get_node_name(
            node.internal_node_meta)
        node.pod_cidrs = kubectlutils.get_node_pod_cidrs(
            node.internal_node_meta)

    def _install_bmv2(self, node: K8sNode):
        containerutils.copy_and_run_script_in_container(
            node.container_id, self._BMV2_PATH, f'/home/{self._BMV2_FILENAME}')
        print(f'Installed bmv2 on: {node.name}')

    def _handle_p4_params(self, node: K8sNode):
        params = node.p4_params

        if params.host_script_path is not None:
            containerutils.copy_to_container(node.container_id, str(
                params.host_script_path.absolute()), self._get_p4_script_container_path(params))

    def _get_p4_script_container_path(self, p4_params: P4Params) -> str:
        return f'/home/{p4_params.host_script_path.name}'

    def _setup_p4_iface_meta(self, node: K8sNode):
        node.p4_net_iface = NetIface(
            f'p4_neth{iputils.random_iface_suffix()}', None, None)
        node.p4_internal_iface = NetIface(
            f'p4_inteth{iputils.random_iface_suffix()}', None, None)

    def _assert_p4_can_be_run_on(self, node: K8sNode):
        assert (node.has_p4_nic and
                node.p4_internal_iface is not None and
                node.p4_net_iface is not None and
                node.p4_params.run_nic), f"P4 NIC can't be run on {node.name}"

    def _resolve_hostnames(self) -> list[str]:
        return list(it.chain(*map(iputils.resolve_hostnames_to_ipv4, self._HOSTNAMES_TO_ROUTE_VIA_HOST)))
