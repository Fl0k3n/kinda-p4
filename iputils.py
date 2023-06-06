import re
import socket
import subprocess as sp
from dataclasses import dataclass


@dataclass
class NetIface:
    name: str
    ipv4: str
    netmask: int


def run_in_namespace(netns: str, *commands: list[str]) -> sp.CompletedProcess[str]:
    return sp.run(['sudo', 'ip', 'netns', 'exec', netns, *commands], capture_output=True, text=True)


def set_netns_iface_state(netns: str, iface_name: str, up: bool):
    run_in_namespace(netns, 'ip', 'link', 'set',
                     iface_name, 'up' if up else 'down')


def assign_ipv4(netns: str, iface: NetIface):
    run_in_namespace(netns, 'ip', 'address', 'add',
                     f'{iface.ipv4}/{iface.netmask}', 'dev', iface.name)


def connect_namespaces(netns1: str, netns2: str, iface1: NetIface, iface2: NetIface, set_up: bool = True):
    run_in_namespace(netns1, 'ip', 'link',  'add', iface1.name,
                     'type', 'veth', 'peer', 'name', iface2.name)
    run_in_namespace(netns1, 'ip', 'link', 'set', iface2.name, 'netns', netns2)

    if set_up:
        set_netns_iface_state(netns1, iface1.name, True)
        set_netns_iface_state(netns2, iface2.name, True)


def add_default_route(netns: str, gateway_ipv4: str):
    run_in_namespace(netns, 'ip', 'route', 'del', 'default')
    run_in_namespace(netns, 'ip', 'route', 'add',
                     'default', 'via', gateway_ipv4)


def add_route(netns: str, dest_ipv4: str, next_hop: str):
    run_in_namespace(netns, 'ip', 'route', 'add', dest_ipv4, 'via', next_hop)


def get_interface_info(netns: str, iface_name: str) -> NetIface:
    iface_data = run_in_namespace(
        netns, 'ip', 'address', 'show', 'dev', iface_name).stdout

    for line in iface_data.splitlines():
        if match := re.search(r'inet\s(\d+\.\d+\.\d+\.\d+)/(\d+)', line):
            return NetIface(iface_name, match.group(1), int(match.group(2)))

    raise Exception(
        f"Failed to get interface info for {iface_name}, got {iface_data}")


def get_host_interface_in_network_with(ipv4: str, netmask: int) -> str:
    # TODO
    assert netmask == 16, 'assuming /16 mask'
    output = sp.run(['ip', 'address'], capture_output=True, text=True).stdout
    return re.search(f'inet\s({".".join(ipv4.split(".")[:2])}\.\d+\.\d+)/{netmask}', output).group(1)


def add_dnat_rule(netns: str, src_ipv4: str, prev_dest_ipv4: str, new_dest_ipv4: str):
    run_in_namespace(netns, 'iptables', '-t', 'nat', '-A', 'OUTPUT', '-d',
                     prev_dest_ipv4, '-s', src_ipv4, '-j', 'DNAT', '--to-destination', new_dest_ipv4)


def resolve_ipv4_addresses(hostname: str) -> list[str]:
    addrs = [res[4][0] for res in socket.getaddrinfo(
        hostname, None, family=socket.AF_INET)]

    assert addrs, f'Failed to resolve {hostname}'

    return list(set(addrs))
