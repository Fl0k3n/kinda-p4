from abc import ABC

from util.iputils import NetIface


class K8sNode(ABC):
    def __init__(self, name: str, has_p4_nic: bool = False) -> None:
        self.name = name
        self.has_p4_nic = has_p4_nic

        self.net_iface: NetIface = None
        self.container_id: str = None
        self.pid: str = None
        self.netns_name: str = None

        # internal interface created by kind
        self.internal_cluster_iface: NetIface = None


class ControlNode(K8sNode):
    pass


class WorkerNode(K8sNode):
    pass
