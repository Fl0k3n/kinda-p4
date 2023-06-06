from abc import ABC

from iputils import NetIface


class K8sNode(ABC):
    def __init__(self, name: str, has_p4_nic: bool = False) -> None:
        self.name = name
        self.has_p4_nic = has_p4_nic
        self.ifaces: dict[str, NetIface] = {}

        self.container_id: str = None
        self.pid: str = None
        self.netns_name: str = None
        self.internal_ipv4: str = None
        self.internal_netmask: int = None

    def get_ifaces(self) -> list[NetIface]:
        return list(self.ifaces.values())

    def add_iface(self, iface: NetIface):
        self.ifaces[iface.name] = iface


class ControlNode(K8sNode):
    pass


class WorkerNode(K8sNode):
    pass
