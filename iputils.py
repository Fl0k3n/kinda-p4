import subprocess as sp


def run_in_namespace(netns: str, *commands: list[str]):
    return sp.run(['sudo', 'ip', 'netns', 'exec', netns, *commands])


def set_netns_iface_state(netns: str, iface: str, up: bool):
    run_in_namespace(netns, 'ip', 'link', 'set', iface, 'up' if up else 'down')


def assign_ipv4(netns: str, iface: str, ipv4: str, netmask: int):
    run_in_namespace(netns, 'ip', 'address', 'add',
                     f'{ipv4}/{netmask}', 'dev', iface)


def connect_namespaces(netns1: str, netns2: str, iface1_name: str, iface2_name: str, set_up: bool = True):
    run_in_namespace(netns1, 'ip', 'link',  'add', iface1_name,
                     'type', 'veth', 'peer', 'name', iface2_name)
    run_in_namespace(netns1, 'ip', 'link', 'set', iface2_name, 'netns', netns2)

    if set_up:
        set_netns_iface_state(netns1, iface1_name, True)
        set_netns_iface_state(netns2, iface2_name, True)


def add_default_route(netns: str, gateway_ipv4: str):
    run_in_namespace(netns, 'ip', 'route', 'del', 'default')
    run_in_namespace(netns, 'ip', 'route', 'add',
                     'default', 'via', gateway_ipv4)
