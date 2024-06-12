from Kathara.model.Lab import Lab

from KatharaBackedNet import (KatharaBackedCluster, container_id, copy_file,
                              execute_simple_switch_cmds, run_in_container,
                              simple_switch_CLI)
from util.iputils import NetIface, TrafficControlInfo
from util.p4 import P4Params

network = Lab("test1")

r1 = network.get_or_new_machine('r1')
network.connect_machine_to_link(r1.name, 'A')
network.connect_machine_to_link(r1.name, 'B')

r1.update_meta(args={
    # "image": "jaxa/p4app-epoch-moje",
    "image": "flok3n/p4c-epoch:latest",
    "exec_commands": [
        "ip link set eth0 address 00:00:0a:00:00:04",
        "ip link set eth1 address 00:00:0a:00:00:05",
        "ethtool -K eth0 rx off tx off",
        "ethtool -K eth1 rx off tx off",
        *simple_switch_CLI(
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.0.2/32 => 00:00:0a:00:00:04 00:00:0a:00:00:01 1',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.1.0/24 => 00:00:0a:00:00:05 00:00:0a:00:00:06 2',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.2.0/24 => 00:00:0a:00:00:05 00:00:0a:00:00:06 2',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.3.0/24 => 00:00:0a:00:00:05 00:00:0a:00:00:06 2',
            'table_add ingress.Forward.arp_exact ingress.Forward.reply_arp 10.10.0.1 => 00:00:0a:00:00:04',
            'table_add ingress.Forward.arp_exact ingress.Forward.reply_arp 10.10.1.1 => 00:00:0a:00:00:05',
            'table_add tb_activate_source activate_source 1 =>',
            # 'table_add tb_int_source configure_source 10.10.0.2&&&0xFFFFFFFF 10.10.3.2&&&0xFFFFFFFF 0x11FF&&&0xFFFF 0x22FF&&&0xFFFF => 4 10 8 0xCC00 0',
            'table_add tb_int_source configure_source 10.10.0.2&&&0xFFFFFFFF 10.10.3.2&&&0xFFFFFFFF 0x11FF&&&0xFFFF 0x22FF&&&0xFFFF => 4 10 8 0xFF00 0',
            'table_add tb_int_transit configure_transit 0.0.0.0/0 => 1 1500',
        ),
        "simple_switch -i 1@eth0 -i 2@eth1 int2.json",
    ]
})

r2 = network.get_or_new_machine('r2')
network.connect_machine_to_link(r2.name, 'B')
network.connect_machine_to_link(r2.name, 'C')

r2.update_meta(args={
    # "image": "jaxa/p4app-epoch-moje",
    "image": "flok3n/p4c-epoch:latest",
    "exec_commands": [
        "ip link set eth0 address 00:00:0a:00:00:06",
        "ip link set eth1 address 00:00:0a:00:00:07",
        "ethtool -K eth0 rx off tx off",
        "ethtool -K eth1 rx off tx off",
        *simple_switch_CLI(
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.0.0/24 => 00:00:0a:00:00:06 00:00:0a:00:00:05 1',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.1.0/24 => 00:00:0a:00:00:06 00:00:0a:00:00:05 1',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.2.0/24 => 00:00:0a:00:00:07 00:00:0a:00:00:08 2',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.3.0/24 => 00:00:0a:00:00:07 00:00:0a:00:00:08 2',
            'table_add tb_int_transit configure_transit 0.0.0.0/0 => 2 1500',
        ),
        "simple_switch -i 1@eth0 -i 2@eth1 int2.json",
    ]
})

r3 = network.get_or_new_machine('r3')
network.connect_machine_to_link(r3.name, 'C')
network.connect_machine_to_link(r3.name, 'D')

r3.update_meta(args={
    # "image": "jaxa/p4app-epoch-moje",
    "image": "flok3n/p4c-epoch:latest",
    "exec_commands": [
        "ip link set eth0 address 00:00:0a:00:00:08",
        "ip link set eth1 address 00:00:0a:00:00:09",
        "ip link set eth2 address 00:00:0a:00:00:0a",
        "ethtool -K eth0 rx off tx off",
        "ethtool -K eth1 rx off tx off",
        "ethtool -K eth2 rx off tx off",
        *simple_switch_CLI(
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.0.0/24 => 00:00:0a:00:00:08 00:00:0a:00:00:07 1',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.1.0/24 => 00:00:0a:00:00:08 00:00:0a:00:00:07 1',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.2.0/24 => 00:00:0a:00:00:08 00:00:0a:00:00:07 1',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.3.2/32 => 00:00:0a:00:00:09 00:00:0a:00:00:02 2',
            'table_add ingress.Forward.arp_exact ingress.Forward.reply_arp 10.10.2.2 => 00:00:0a:00:00:08',
            'table_add ingress.Forward.arp_exact ingress.Forward.reply_arp 10.10.3.1 => 00:00:0a:00:00:09',
            'table_add ingress.Forward.arp_exact ingress.Forward.reply_arp 10.10.4.1 => 00:00:0a:00:00:0a',
            'table_add tb_int_sink configure_sink 2 => 3',
            'mirroring_add 1 3',
            'table_add tb_int_reporting send_report 0.0.0.0/0 => 00:00:0a:00:00:0a 10.10.4.1 00:00:0a:00:00:03 10.10.4.2 6000',
            'table_add tb_int_transit configure_transit 0.0.0.0/0 => 3 1500',
        ),
        "simple_switch -i 1@eth0 -i 2@eth1 -i 3@eth2 int2.json",
    ]
})

h1 = network.get_or_new_machine('h1')
h2 = network.get_or_new_machine('h2')
network.connect_machine_to_link(h1.name, 'A')
network.connect_machine_to_link(h2.name, 'D')

h1.update_meta(args={
    "image": "kathara/base",
    "exec_commands": [
        "ifconfig eth0 10.10.0.2/24 up",
        "ip link set eth0 address 00:00:0a:00:00:01",
        "ip route add default via 10.10.0.1",
        "ethtool -K eth0 rx off tx off",
        "ip link set dev eth0 mtu 1000"
    ]
})

h2.update_meta(args={
    "image": "kathara/base",
    "exec_commands": [
        "ifconfig eth0 10.10.3.2/24 up",
        "ip link set eth0 address 00:00:0a:00:00:02",
        "ip route add default via 10.10.3.1",
        "ethtool -K eth0 rx off tx off",
        "ip link set dev eth0 mtu 1000",
    ]
})

collector = network.get_or_new_machine('col')
network.connect_machine_to_link(r3.name, 'E')
network.connect_machine_to_link(collector.name, 'E')

collector.update_meta(args={
    "image": "kathara/base",
    "exec_commands": [
        "ifconfig eth0 10.10.4.2/24 up",
        "ip link set eth0 address 00:00:0a:00:00:03",
        "ip route add default via 10.10.4.1",
        "ethtool -K eth0 rx off tx off",
    ]
})


'''
p4c-bm2-ss --p4v 16 parent/int_v2.0/int.p4 -o "int.json" -DBMV2
p4c-bm2-ss --p4v 16 /p4/int.p4 -o "int.json" -DBMV2
'''

with KatharaBackedCluster('test-cluster', network) as cluster:
    for r in (r1, r2, r3):
        execute_simple_switch_cmds(r.name)
    copy_file(
        '/home/flok3n/develop/virtual/ubuntu20/src/examples/k8s/sr-job/sender.py', h1.name)
    copy_file(
        '/home/flok3n/develop/virtual/ubuntu20/src/examples/k8s/sr-job/sender_tcp.py', h1.name)
    copy_file(
        '/home/flok3n/develop/virtual/ubuntu20/src/examples/k8s/sr-job/receiver.py', h2.name)
    copy_file(
        '/home/flok3n/develop/virtual/ubuntu20/src/examples/k8s/sr-job/receiver_tcp.py', h2.name)
    copy_file('/home/flok3n/develop/virtual/telemetry2/int-platforms/platforms/bmv2-mininet/int.p4app/utils/int_collector_logging.py', collector.name)
    run_in_container(collector.name, 'mkdir -p /tmp/p4app_logs')
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
