import re
import socket
import subprocess as sp
from dataclasses import dataclass


@dataclass
class NetIface:
    name: str
    ipv4: str
    netmask: int


def _run_sp(*commands: list[str]) -> sp.CompletedProcess[str]:
    return sp.run(['sudo', *commands], capture_output=True, text=True)


def _iptables_mode(enabled: bool) -> str:
    return '-A' if enabled else '-D'


def run_in_namespace(netns: str | None, *commands: list[str]) -> sp.CompletedProcess[str]:
    return _run_sp('ip', 'netns', 'exec', netns, *commands) if netns is not None else _run_sp(*commands)


def set_iface_state(netns: str | None, iface_name: str, up: bool):
    run_in_namespace(netns, 'ip', 'link', 'set',
                     iface_name, 'up' if up else 'down')


def assign_ipv4(netns: str | None, iface: NetIface):
    run_in_namespace(netns, 'ip', 'address', 'add',
                     f'{iface.ipv4}/{iface.netmask}', 'dev', iface.name)


def connect_namespaces(netns1: str | None, netns2: str, iface1: NetIface, iface2: NetIface, set_up: bool = True):
    run_in_namespace(netns1, 'ip', 'link',  'add', iface1.name,
                     'type', 'veth', 'peer', 'name', iface2.name)
    run_in_namespace(netns1, 'ip', 'link', 'set', iface2.name, 'netns', netns2)

    if set_up:
        set_iface_state(netns1, iface1.name, True)
        set_iface_state(netns2, iface2.name, True)


def add_default_route(netns: str | None, gateway_ipv4: str):
    run_in_namespace(netns, 'ip', 'route', 'del', 'default')
    run_in_namespace(netns, 'ip', 'route', 'add',
                     'default', 'via', gateway_ipv4)


def add_route(netns: str | None, dest_ipv4: str, next_hop: str):
    run_in_namespace(netns, 'ip', 'route', 'add', dest_ipv4, 'via', next_hop)


def get_interface_info(netns: str | None, iface_name: str) -> NetIface:
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


def add_dnat_rule(netns: str | None, src_ipv4: str, prev_dest_ipv4: str, new_dest_ipv4: str):
    run_in_namespace(netns, 'iptables', '-t', 'nat', '-A', 'OUTPUT', '-d',
                     prev_dest_ipv4, '-s', src_ipv4, '-j', 'DNAT', '--to-destination', new_dest_ipv4)


def resolve_hostnames_to_ipv4(hostname: str) -> list[str]:
    addrs = [res[4][0] for res in socket.getaddrinfo(
        hostname, None, family=socket.AF_INET)]

    assert addrs, f'Failed to resolve {hostname}'

    return list(set(addrs))


def assign_bridge_master(netns: str | None, veth: NetIface, bridge: NetIface):
    run_in_namespace(netns, 'ip', 'link', 'set',
                     veth.name, 'master', bridge.name)


def create_bridge(netns: str | None, bridge: NetIface):
    run_in_namespace(netns, 'ip', 'link', 'add', bridge.name, 'type', 'bridge')
    assign_ipv4(netns, bridge)
    set_iface_state(netns, bridge.name, True)


def connect_container_to_bridge(bridge: NetIface, host_veth: NetIface, container_veth: NetIface, container_netns: str):
    run_in_namespace(None, 'ip', 'link', 'add', host_veth.name,
                     'type', 'veth', 'peer', 'name', container_veth.name)
    run_in_namespace(None, 'ip', 'link', 'set',
                     container_veth.name, 'netns', container_netns)

    assign_ipv4(container_netns, container_veth)
    set_iface_state(None, host_veth.name, True)
    set_iface_state(container_netns, container_veth.name, True)

    assign_bridge_master(None, host_veth, bridge)


def set_forwarding_through(netns: str | None, iface: NetIface, enabled: bool):
    mode = _iptables_mode(enabled)
    run_in_namespace(netns, 'iptables', mode, 'FORWARD',
                     '-o', iface.name, '-j', 'ACCEPT')
    run_in_namespace(netns, 'iptables', mode, 'FORWARD',
                     '-i', iface.name, '-j', 'ACCEPT')


def set_bridged_traffic_masquerading(netns: str | None, bridge: NetIface, enabled: bool):
    mode = _iptables_mode(enabled)
    run_in_namespace(netns, 'iptables', '-t', 'nat', mode, 'POSTROUTING', '-s',
                     f'{bridge.ipv4}/{bridge.netmask}', '!', '-o', bridge.name, '-j', 'MASQUERADE')


def masquerade_internet_facing_traffic(netns: str | None, src_iface: NetIface, forwarding_iface: NetIface):
    run_in_namespace(netns, 'iptables', '-t', 'nat', '-A', 'POSTROUTING', '-s',
                     f'{src_iface.ipv4}/{src_iface.netmask}', '-o', forwarding_iface.name, '-j', 'MASQUERADE')


def delete_iface(netns: str | None, iface: NetIface):
    run_in_namespace(netns, 'ip', 'link', 'del', iface.name)
