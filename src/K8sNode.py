from abc import ABC

from util.iputils import NetIface
from util.kubectlutils import Cidr, NodeInfo
from util.p4 import P4Params


class K8sNode(ABC):
    def __init__(self, name: str, has_p4_nic: bool = False, p4_params: P4Params = None) -> None:
        self.name = name
        self.has_p4_nic = has_p4_nic
        self.p4_params = p4_params

        self.p4_net_iface: NetIface = None
        self.p4_internal_iface: NetIface = None

        self.net_iface: NetIface = None
        self.container_id: str = None
        self.pid: str = None
        self.netns_name: str = None

        # internal interface created by kind
        self.internal_cluster_iface: NetIface = None

        self.internal_node_meta: NodeInfo = None
        self.internal_node_name: str = None
        self.pod_cidrs: list[Cidr] = None


class ControlNode(K8sNode):
    pass


class WorkerNode(K8sNode):
    pass
