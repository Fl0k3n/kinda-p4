from Kathara.model.Lab import Lab

from KatharaBackedNet import KatharaBackedCluster, container_id
from util.iputils import NetIface, TrafficControlInfo
from util.p4 import P4Params


def simple_switch_CLI(*cmds: list[str]) -> list[str]:
    return [
        "echo '#!/bin/bash' >> s.sh",
        "echo 'while [[ $(pgrep simple_switch) -eq 0 ]]; do sleep 1; done' >> s.sh",
        "echo 'until simple_switch_CLI <<< 'help'; do sleep 1; done' >> s.sh",
        *[f"echo \"echo '{cmd}' | simple_switch_CLI\" >> s.sh" for cmd in cmds],
        "chmod u+x s.sh",
    ]


network = Lab("test1")

r1 = network.get_or_new_machine('r1')
network.connect_machine_to_link(r1.name, 'A')
network.connect_machine_to_link(r1.name, 'B')

r1.update_meta(args={
    "image": "jaxa/p4app-epoch-moje",
    "exec_commands": [
        "ip link set eth0 address 00:00:0a:00:00:03",
        "ip link set eth1 address 00:00:0a:00:00:04",
        *simple_switch_CLI(
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.1.2/32 => 00:00:0a:00:00:03 00:00:0a:00:00:01 1',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.2.2/32 => 00:00:0a:00:00:04 00:00:0a:00:00:02 2',
            'table_add ingress.Forward.arp_exact ingress.Forward.reply_arp 10.10.1.1 => 00:00:0a:00:00:03',
            'table_add ingress.Forward.arp_exact ingress.Forward.reply_arp 10.10.2.1 => 00:00:0a:00:00:04',
        ),
        "simple_switch -i 1@eth0 -i 2@eth1 int.json",
    ]
})

# r2 = network.get_or_new_machine('r2')
# network.connect_machine_to_link(r2.name, 'B')
# network.connect_machine_to_link(r2.name, 'C')

# r2.update_meta(args={
#     "image": "jaxa/p4app-epoch-moje",
#     "exec_commands": [
#         # "ifconfig eth0 10.10.1.2/24 up",
#         # "ifconfig eth1 10.10.2.1/24 up",
#         # "route add -net 10.10.0.0/24 gw 10.10.1.1 dev eth0",
#         # "ip route add default via 10.10.1.1",
#         "simple_switch -i 1@eth0 -i 2@eth1 int.json",
#     ]
# })

h1 = network.get_or_new_machine('h1')
h2 = network.get_or_new_machine('h2')
network.connect_machine_to_link(h1.name, 'A')
network.connect_machine_to_link(h2.name, 'B')

h1.update_meta(args={
    "image": "kathara/base",
    "exec_commands": [
        "ifconfig eth0 10.10.1.2/24 up",
        "ip link set eth0 address 00:00:0a:00:00:01",
        "ip route add default via 10.10.1.1",
    ]
})

h2.update_meta(args={
    "image": "kathara/base",
    "exec_commands": [
        "ifconfig eth0 10.10.2.2/24 up",
        "ip link set eth0 address 00:00:0a:00:00:02",
        "ip route add default via 10.10.2.1",
    ]
})

'''
p4c-bm2-ss --p4v 16 parent/int_v2.0/int.p4 -o "int.json" -DBMV2
'''

with KatharaBackedCluster('test-cluster', network) as cluster:
    print('debug')
#     cluster.enable_internet_access_via(container_id(r2))
#     cluster.enable_kubectl_routing_through_virtual_network()

#     cluster.add_worker('w1', with_p4_nic=False, p4_params=P4Params(
#         initial_compiled_script_host_path='./examples/p4/basic_arp_compiled.json', run_nic=True))
#     cluster.add_worker('w2', with_p4_nic=True, p4_params=P4Params(
#         initial_compiled_script_host_path='./examples/p4/basic_arp_compiled.json', run_nic=True))
#     cluster.add_control('c1', with_p4_nic=False)

#     cluster.connect_with_container(
#         'w1',
#         node_iface=NetIface('eth10k', '10.10.0.2', 24,
#                             egress_traffic_control=TrafficControlInfo(latency_ms=500, rate_kbitps=1000, burst_kbitps=16)),
#         container_id=container_id(r1),
#         container_iface=NetIface('br_1c', '10.10.0.1', 24)
#     )

#     cluster.connect_with_container(
#         'w2',
#         node_iface=NetIface('eth10k', '10.10.0.3', 24),
#         container_id=container_id(r1),
#         container_iface=NetIface('br_1c', '10.10.0.1', 24)
#     )

#     cluster.connect_with_container(
#         'c1',
#         node_iface=NetIface('eth10k', '10.10.2.2', 24),
#         container_id=container_id(r2),
#         container_iface=NetIface('eth10c', '10.10.2.1', 24)
#     )

#     cluster.build()
#     print('press enter to terminate cluster')
