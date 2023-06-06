from abc import ABC


class K8sNode(ABC):
    def __init__(self, name: str, ipv4: str, netmask: int) -> None:
        self.name = name
        self.ipv4 = ipv4
        self.netmask = netmask

        self.net_iface = 'eth10'
        self.container_id: str = None
        self.pid: str = None
        self.netns_name: str = None
        self.internal_ipv4: str = None
        self.internal_netmask: int = None
