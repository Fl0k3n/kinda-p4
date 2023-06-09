import json
import subprocess as sp
from typing import Any

from util.iputils import Cidr

KUBECTL = 'kubectl'

NodesInfo = dict[str, Any]
NodeInfo = dict[str, Any]


def get_nodes_info() -> NodesInfo:
    res = json.loads(sp.run(
        [KUBECTL, 'get', 'nodes', '-o', 'json'], capture_output=True, text=True).stdout)
    assert res['apiVersion'] == 'v1', 'Unsupported kubernetes api version for node resource'
    return res


def get_info_of_node_with_internal_ip(nodes_info: NodesInfo, ipv4: str):
    for item in nodes_info['items']:
        if any(x['address'] == ipv4 for x in item['status']['addresses'] if x['type'] == 'InternalIP'):
            return item

    raise Exception(f"Failed to find node with ip: {ipv4}")


def get_node_name(node_info: NodeInfo) -> str:
    return node_info['metadata']['name']


def get_node_pod_cidrs(node_info: NodeInfo) -> list[Cidr]:
    cidrs = [x.split('/') for x in node_info['spec']['podCIDRs']]
    return [Cidr(ipv4, int(netmask)) for ipv4, netmask in cidrs]
