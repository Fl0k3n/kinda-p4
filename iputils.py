import subprocess as sp
from dataclasses import dataclass


@dataclass
class NetIface:
    name: str
    ipv4: str
    netmask: int


def run_in_namespace(netns: str, *commands: list[str]):
    return sp.run(['sudo', 'ip', 'netns', 'exec', netns, *commands])


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
