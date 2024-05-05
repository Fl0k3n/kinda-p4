import random
import re
import socket
import subprocess as sp
from dataclasses import dataclass
from typing import NamedTuple

from util.logger import logger

Netns = str | None
HOST_NS: Netns = None


class Cidr(NamedTuple):
    ipv4: str
    netmask: int

    @property
    def first_octet(self) -> str:
        return get_nth_octet(self.ipv4, 0)

    @property
    def second_octet(self) -> str:
        return get_nth_octet(self.ipv4, 1)

    @property
    def third_octet(self) -> str:
        return get_nth_octet(self.ipv4, 2)

    @property
    def fourth_octet(self) -> str:
        return get_nth_octet(self.ipv4, 3)

    @property
    def masked_ip(self) -> str:
        return f'{self.ipv4}/{self.netmask}'


class TrafficControlInfo(NamedTuple):
    latency_ms: int
    rate_kbitps: int
    burst_kbitps: int


@dataclass
class NetIface:
    name: str
    ipv4: str
    netmask: int
    egress_traffic_control: TrafficControlInfo | None = None
    mac: str | None = None

    @property
    def cidr(self) -> Cidr:
        return Cidr(self.ipv4, self.netmask)


def _run_sp(*commands: list[str], log_error=True) -> sp.CompletedProcess[str]:
    res = sp.run(['sudo', *commands], capture_output=True, text=True)
    if log_error and res.returncode != 0:
        logger.error(
            f'Command {commands}; returned error: {res.returncode}\nstd_err: {res.stderr}')
    return res


def dot_notation_to_decimal(dotted: str) -> int:
    return sum(int(byte) * (256 ** (3 - i)) for i, byte in enumerate(dotted.split('.')))


def decimal_to_dot_notation(decimal_repr: int) -> str:
    parts = []
    for _ in range(4):
        parts.append(str(decimal_repr % 256))
        decimal_repr //= 256
    return '.'.join(reversed(parts))


def mask_size_to_decimal(mask: int) -> int:
    return sum((1 << i) for i in range((32 - mask), 32))


def run_in_namespace(netns: Netns, *commands: list[str], log_error=True) -> sp.CompletedProcess[str]:
    if netns is not None:
        return _run_sp('ip', 'netns', 'exec', netns, *commands, log_error=log_error)
    return _run_sp(*commands, log_error=log_error)


def random_iface_suffix() -> str:
    return str(random.randint(100, 999))


def create_veth_pair(netns: Netns, iface1: NetIface, iface2: NetIface, set_up: bool = False):
    run_in_namespace(netns, 'ip', 'link', 'add', iface1.name,
                     'type', 'veth', 'peer', 'name', iface2.name)
    if set_up:
        set_iface_state(netns, iface1.name, True)
        set_iface_state(netns, iface2.name, True)


def move_iface_to_netns(src_ns: Netns, dest_ns: Netns, iface: NetIface):
    assert src_ns != dest_ns
    run_in_namespace(src_ns, 'ip', 'link', 'set', iface.name, 'netns', dest_ns)


def set_iface_state(netns: Netns, iface_name: str, up: bool):
    run_in_namespace(netns, 'ip', 'link', 'set',
                     iface_name, 'up' if up else 'down')


def assign_ipv4(netns: Netns, iface: NetIface):
    run_in_namespace(netns, 'ip', 'address', 'add',
                     f'{iface.ipv4}/{iface.netmask}', 'dev', iface.name)


def assign_mac(netns: Netns, iface: NetIface):
    assert iface.mac is not None
    run_in_namespace(netns, 'ip', 'link', 'set',
                     iface.name, 'address', iface.mac)


def connect_namespaces(netns1: Netns, netns2: Netns, iface1: NetIface, iface2: NetIface, set_up: bool = True):
    assert netns1 != netns2
    create_veth_pair(netns1, iface1, iface2)
    move_iface_to_netns(netns1, netns2, iface2)

    if set_up:
        set_iface_state(netns1, iface1.name, True)
        set_iface_state(netns2, iface2.name, True)


def add_default_route(netns: Netns, gateway_ipv4: str):
    run_in_namespace(netns, 'ip', 'route', 'del', 'default', log_error=False)
    run_in_namespace(netns, 'ip', 'route', 'add',
                     'default', 'via', gateway_ipv4)


def add_route(netns: Netns, dest_ipv4: str, next_hop: str):
    run_in_namespace(netns, 'ip', 'route', 'add', dest_ipv4, 'via', next_hop)


def del_route(netns: Netns, dest_ipv4: str, next_hop: str):
    run_in_namespace(netns, 'ip', 'route', 'del', dest_ipv4, 'via', next_hop)


def get_interface_info(netns: Netns, iface_name: str) -> NetIface:
    iface_data = run_in_namespace(
        netns, 'ip', 'address', 'show', 'dev', iface_name).stdout

    for line in iface_data.splitlines():
        if match := re.search(r'inet\s(\d+\.\d+\.\d+\.\d+)/(\d+)', line):
            return NetIface(iface_name, match.group(1), int(match.group(2)))

    raise Exception(
        f"Failed to get interface info for {iface_name}, got {iface_data}")


def get_host_ipv4_in_network_with(ipv4: str, netmask: int) -> str:
    # TODO
    assert netmask == 16, 'assuming /16 mask'
    output = _run_sp('ip', 'address').stdout
    return re.search(f'inet\s({".".join(ipv4.split(".")[:2])}\.\d+\.\d+)/{netmask}', output).group(1)


def add_dnat_rule(netns: Netns, src_ipv4: str, prev_dest_ipv4: str, new_dest_ipv4: str):
    run_in_namespace(netns, 'iptables', '-t', 'nat', '-I', 'OUTPUT', '-d',
                     prev_dest_ipv4, '-j', 'DNAT', '--to-destination', new_dest_ipv4)


def resolve_hostnames_to_ipv4(hostname: str) -> list[str]:
    addrs = [res[4][0] for res in socket.getaddrinfo(
        hostname, None, family=socket.AF_INET)]

    assert addrs, f'Failed to resolve {hostname}'

    return list(set(addrs))


def assign_bridge_master(netns: Netns, veth: NetIface, bridge: NetIface):
    run_in_namespace(netns, 'ip', 'link', 'set',
                     veth.name, 'master', bridge.name)


def create_bridge(netns: Netns, bridge: NetIface):
    run_in_namespace(netns, 'ip', 'link', 'add', bridge.name, 'type', 'bridge')
    assign_ipv4(netns, bridge)
    set_iface_state(netns, bridge.name, True)


def connect_container_to_bridge(bridge: NetIface, host_veth: NetIface, container_veth: NetIface, container_netns: str):
    create_veth_pair(HOST_NS, host_veth, container_veth)
    move_iface_to_netns(HOST_NS, container_netns, container_veth)

    assign_ipv4(container_netns, container_veth)
    set_iface_state(HOST_NS, host_veth.name, True)
    set_iface_state(container_netns, container_veth.name, True)

    assign_bridge_master(HOST_NS, host_veth, bridge)


def set_forwarding_through(netns: Netns, iface: NetIface, enabled: bool):
    mode = '-A' if enabled else '-D'
    run_in_namespace(netns, 'iptables', mode, 'FORWARD',
                     '-o', iface.name, '-j', 'ACCEPT')
    run_in_namespace(netns, 'iptables', mode, 'FORWARD',
                     '-i', iface.name, '-j', 'ACCEPT')


def set_bridged_traffic_masquerading(netns: Netns, bridge: NetIface, enabled: bool):
    mode = '-A' if enabled else '-D'
    run_in_namespace(netns, 'iptables', '-t', 'nat', mode, 'POSTROUTING', '-s',
                     f'{bridge.ipv4}/{bridge.netmask}', '!', '-o', bridge.name, '-j', 'MASQUERADE')


def masquerade_internet_facing_traffic(netns: Netns, src: Cidr, forwarding_iface: NetIface):
    run_in_namespace(netns, 'iptables', '-t', 'nat', '-A', 'POSTROUTING', '-s',
                     f'{src.ipv4}/{src.netmask}', '-o', forwarding_iface.name, '-j', 'MASQUERADE')


def create_gre_tunnel(netns: Netns, tunnel_iface: NetIface, src_ipv4: str, dst_ipv4: str, set_up: bool = True):
    run_in_namespace(netns, 'ip', 'tunnel', 'add',
                     tunnel_iface.name, 'mode', 'gre', 'remote', dst_ipv4, 'local', src_ipv4, 'ttl', '255')
    assign_ipv4(netns, tunnel_iface)
    if set_up:
        set_iface_state(netns, tunnel_iface.name, True)


def flush_established_connections(netns: Netns):
    run_in_namespace(netns, 'conntrack', '-F')


def apply_egress_traffic_control(netns: Netns, iface: NetIface):
    tc = iface.egress_traffic_control
    if any(field is None for field in tc):
        raise Exception('traffic control requires all fields to be set')

    command = f'tc qdisc add dev {iface.name} root tbf'
    if tc.latency_ms is not None:
        command += f' latency {tc.latency_ms}ms'
    if tc.rate_kbitps is not None:
        command += f' rate {tc.rate_kbitps}kbit'
    if tc.burst_kbitps is not None:
        command += f' burst {tc.burst_kbitps}kbit'

    run_in_namespace(netns, *command.split())


def is_in_same_subnet(cidr1: Cidr, cidr2: Cidr) -> bool:
    mask = mask_size_to_decimal(min(cidr1.netmask, cidr2.netmask))
    ip1 = dot_notation_to_decimal(cidr1.ipv4)
    ip2 = dot_notation_to_decimal(cidr2.ipv4)
    return ((ip1 & mask) ^ (ip2 & mask)) == 0


def get_subnet(cidr: Cidr) -> Cidr:
    mask = mask_size_to_decimal(cidr.netmask)
    ip = dot_notation_to_decimal(cidr.ipv4)
    subnet_ip = decimal_to_dot_notation(ip & mask)
    return Cidr(subnet_ip, cidr.netmask)


def get_nth_octet(ipv4: str, n: int) -> str:
    return ipv4.split('.')[n]


def delete_iface(netns: Netns, iface: NetIface):
    run_in_namespace(netns, 'ip', 'link', 'del', iface.name)


def delete_namespace(parent_ns: Netns, ns_to_delete: str):
    run_in_namespace(parent_ns, 'ip', 'netns', 'delete', ns_to_delete)
