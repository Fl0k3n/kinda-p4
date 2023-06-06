from K8sNode import K8sNode


class WorkerNode(K8sNode):
    def __init__(self, name: str, ipv4: str, netmask: int, has_p4_nic: bool) -> None:
        super().__init__(name, ipv4, netmask)
        self.has_p4_nic = has_p4_nic
