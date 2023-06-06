import os
import subprocess as sp

import containerutils
import iputils
from ControlNode import ControlNode
from K8sNode import K8sNode
from WorkerNode import WorkerNode

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class NodeInitializer:
    _KIND_IFACE_NAME = 'eth0'
    _NODE_INIT_SCRIPT_FILENAME = 'node_init.sh'
    _BMV2_FILENAME = 'bmv2_install.sh'
    _NODE_INIT_PATH = os.path.join(_THIS_DIR, _NODE_INIT_SCRIPT_FILENAME)
    _BMV2_PATH = os.path.join(_THIS_DIR, _BMV2_FILENAME)

    def assing_container_ids(self, cluster_name: str, workers: list[WorkerNode], controls: list[ControlNode]):
        docker_output = sp.run(['sudo', 'docker', 'ps'],
                               capture_output=True, text=True)
        workers_iter = iter(workers)
        controls_iter = iter(controls)

        for line in docker_output.stdout.splitlines():
            if cluster_name in line:
                parts = line.split()
                if 'worker' in line:
                    worker = next(workers_iter)
                    worker.container_id = parts[0]
                else:
                    control = next(controls_iter)
                    control.container_id = parts[0]

        assert next(workers_iter, None) is None and next(controls_iter, None) is None, \
            'Failed to assign container ids to some nodes'

    def init_worker(self, node: WorkerNode):
        print(f'Initializing worker: {node.name}')
        self._init_container_requirements(node)

        if node.has_p4_nic:
            self._install_bmv2(node)

        iputils.set_netns_iface_state(
            node.netns_name, self._KIND_IFACE_NAME, up=False)
        print(f'worker: {node.name} ready')

    def init_control(self, node: ControlNode):
        print(f'Initializing control plane node: {node.name}')
        self._init_container_requirements(node)
        iputils.set_netns_iface_state(
            node.netns_name, self._KIND_IFACE_NAME, up=False)
        print(f'control plane node: {node.name} ready')

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
