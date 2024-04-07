import os
import subprocess as sp
from typing import IO

from util.logger import logger

KUBECONFIG_PATH = os.path.join(os.environ['HOME'], '.kube', 'config')


def prepare_kind_cfg_file(file: IO[bytes], control_nodes_count: int, worker_nodes_count: int):
    lines = ([
        'kind: Cluster',
        'apiVersion: kind.x-k8s.io/v1alpha4',
        'nodes:',
        *['- role: control-plane' for _ in range(control_nodes_count)],
        *['- role: worker' for _ in range(worker_nodes_count)],
        ''
    ])

    file.write('\n'.join(lines).encode())
    file.flush()


def run_cluster(name: str, kind_cfg_file_path: str, timeout: float):
    kind_sp = sp.Popen(['sudo', 'kind', 'create', 'cluster', '--name', name, '--config', kind_cfg_file_path],
                       stdout=sp.PIPE,
                       text=True)
    kind_sp.wait(timeout)
    assert kind_sp.returncode == 0, 'Cluster creation failed'


def update_kubectl_cfg(cluster_name: str, kubeconfig_path: str):
    kubeconfig = sp.run(['sudo', 'kind', 'get', 'kubeconfig',
                        '--name', cluster_name], capture_output=True, text=True).stdout
    with open(kubeconfig_path, 'w') as f:
        f.write(kubeconfig)


def delete_cluster(cluster_name: str):
    res = sp.run(['sudo', 'kind', 'delete', 'clusters',
                  cluster_name], capture_output=True, text=True)
    logger.info(res.stdout)
