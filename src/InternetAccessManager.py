import util.iputils as iputils
from constants import KIND_CIDR, POD_CIDR, TUN_CIDR
from K8sNode import K8sNode
from util.iputils import NetIface


class InternetAccessManager:
    def __init__(self) -> None:
        self.internet_gateway_container_netns: str = None
        self.cluster_nodes: list[K8sNode] = None
        self.host_bridge: NetIface = None
        self.host_veth: NetIface = None
        self.container_veth: NetIface = None

    def provision_internet_access(self, cluster_nodes: list[K8sNode]):
        assert self.internet_gateway_container_netns is not None, 'Gateway netns is required'
        self.cluster_nodes = cluster_nodes

        self._create_host_bridge()
        self._connect_gateway_to_bridge()
        self._add_default_route_on_target()
        self._setup_address_translations()

    def teardown_internet_access(self):
        try:
            iputils.set_bridged_traffic_masquerading(
                iputils.HOST_NS, self.host_bridge, False)
            iputils.delete_iface(iputils.HOST_NS, self.host_veth)
            iputils.delete_iface(iputils.HOST_NS, self.host_bridge)
        except Exception as e:
            print("Exception while removing internet access")
            print(e)

    def _create_host_bridge(self):
        self.host_bridge = self._get_host_bridge_meta()
        iputils.create_bridge(iputils.HOST_NS, self.host_bridge)

    def _connect_gateway_to_bridge(self):
        self.host_veth = NetIface(
            f'{self.host_bridge.name}_slave1', None, None)

        container_veth_ip = '.'.join(
            self.host_bridge.ipv4.split('.')[:3]) + '.2'
        self.container_veth = NetIface(
            f'{self.host_bridge.name}_slave2', container_veth_ip, self.host_bridge.netmask)

        iputils.connect_container_to_bridge(
            self.host_bridge, self.host_veth, self.container_veth, self.internet_gateway_container_netns)

    def _add_default_route_on_target(self):
        iputils.add_default_route(
            self.internet_gateway_container_netns, self.host_bridge.ipv4)

    def _setup_address_translations(self):
        iputils.set_forwarding_through(iputils.HOST_NS, self.host_bridge, True)
        iputils.set_bridged_traffic_masquerading(
            iputils.HOST_NS, self.host_bridge, True)

        for subnet in (POD_CIDR, TUN_CIDR):
            iputils.masquerade_internet_facing_traffic(
                self.internet_gateway_container_netns, subnet, self.container_veth)

        for cluster_node in self.cluster_nodes:
            iputils.masquerade_internet_facing_traffic(
                self.internet_gateway_container_netns, cluster_node.net_iface.cidr, self.container_veth)

    def _get_host_bridge_meta(self) -> NetIface:
        # TODO make it more deterministic
        name = f'br_{iputils.random_iface_suffix()}'
        base_subnet = 64
        for subnet in range(base_subnet, 255):
            try:
                iputils.get_host_ipv4_in_network_with(
                    f'{KIND_CIDR.first_octet}.{subnet}.0.0', 16)
            except:
                return NetIface(name, f'{KIND_CIDR.first_octet}.{subnet}.0.1', 16)

        raise Exception("Failed to create bridge on host")
