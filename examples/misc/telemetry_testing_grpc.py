import os

from Kathara.model.Lab import Lab

import util.containerutils as cutils
from net.KatharaBackedNet import (KatharaBackedCluster, container_id,
                                  run_in_kathara_machine)
from net.util import execute_simple_switch_cmds, simple_switch_CLI
from util.iputils import NetIface

network = Lab("test1")

'''
         extern 
           |
          r4 
           |
r1 - r2 - r3-----
|     |    |    | 
w1    w2   w3   c1
'''

r1 = network.get_or_new_machine('r1')
network.connect_machine_to_link(r1.name, 'A')

r1.update_meta(args={
    "image": "flok3n/p4c-epoch_thrift:latest",
    # remember that this creates new interface, fix all references (bump ethX to ethX+1 for all node interfaces after setting bridged: True)
    "bridged": True,
    "ports": [
        "9560:9559"
    ],
    "exec_commands": [
        *simple_switch_CLI(
            'mirroring_add 1 1',
        ),
    ]
})

r2 = network.get_or_new_machine('r2')
network.connect_machine_to_link(r2.name, 'A')
network.connect_machine_to_link(r2.name, 'B')

r2.update_meta(args={
    "image": "flok3n/p4c-epoch_thrift:latest",
    "bridged": True,
    "ports": [
        "9561:9559"
    ],
    "exec_commands": [
        *simple_switch_CLI(),
    ]
})

r3 = network.get_or_new_machine('r3')
network.connect_machine_to_link(r3.name, 'B')
r3.update_meta(args={
    "image": "flok3n/p4c-epoch_thrift:latest",
    "bridged": True,
    "ports": [
        "9562:9559"
    ],
    "exec_commands": [
        *simple_switch_CLI(
            'mirroring_add 1 1',
        ),
    ]
})

r4 = network.get_or_new_machine('r4')
network.connect_machine_to_link(r3.name, 'C')
network.connect_machine_to_link(r4.name, 'C')
r4.update_meta(args={
    "image": "flok3n/p4c-epoch_thrift:latest",
    "bridged": True,
    "ports": [
        "9563:9559"
    ],
    "exec_commands": [
        *simple_switch_CLI(
            'mirroring_add 1 1',
        ),
    ]
})


extern = network.get_or_new_machine('extern')
network.connect_machine_to_link(r4.name, 'E')
network.connect_machine_to_link(extern.name, 'E')

extern.update_meta(args={
    "image": "kathara/base",
    "exec_commands": [
        "ifconfig eth0 10.10.7.2/24 up",
        "ip link set eth0 address 00:00:0a:00:0f:02",
        "ip route add default via 10.10.7.1",
        "ethtool -K eth0 rx off tx off",
        "ip link set dev eth0 mtu 1000"
    ]
})

with KatharaBackedCluster('test-cluster', network) as cluster:
    w1 = cluster.add_worker('w1')
    w2 = cluster.add_worker('w2')
    w3 = cluster.add_worker('w3')
    c1 = cluster.add_control('c1')

    cluster.connect_with_container(
        'w1',
        node_iface=NetIface('eth10k', '10.10.0.2', 24,
                            mac="00:00:0a:00:00:01"),
        container_id=container_id(r1),
        container_iface=NetIface('eth2', '10.10.0.1', 24)
    )

    cluster.connect_with_container(
        'w2',
        node_iface=NetIface('eth10k', '10.10.2.2', 24,
                            mac="00:00:0a:00:00:02"),
        container_id=container_id(r2),
        container_iface=NetIface('eth3', '10.10.2.1', 24)
    )

    cluster.connect_with_container(
        'w3',
        node_iface=NetIface('eth10k', '10.10.4.2', 24,
                            mac="00:00:0a:00:00:03"),
        container_id=container_id(r3),
        container_iface=NetIface('eth3', '10.10.4.1', 24)
    )

    cluster.connect_with_container(
        'c1',
        node_iface=NetIface('eth10k', '10.10.5.2', 24,
                            mac="00:00:0a:00:00:04"),
        container_id=container_id(r3),
        container_iface=NetIface('eth4', '10.10.5.1', 24)
    )

    cluster.build()

    run_in_kathara_machine(r1, commands=[
        "ip link set eth0 address 00:00:0a:00:00:05",
        "ip link set eth2 address 00:00:0a:00:00:06",
        "ethtool -K eth0 rx off tx off",
        "ethtool -K eth2 rx off tx off",
        "simple_switch_grpc -i 1@eth0 -i 2@eth2 --no-p4",
    ])

    run_in_kathara_machine(r2, commands=[
        "ip link set eth0 address 00:00:0a:00:00:07",
        "ip link set eth1 address 00:00:0a:00:00:08",
        "ip link set eth3 address 00:00:0a:00:00:09",
        "ethtool -K eth0 rx off tx off",
        "ethtool -K eth1 rx off tx off",
        "ethtool -K eth3 rx off tx off",
        "simple_switch_grpc -i 1@eth0 -i 2@eth1 -i 3@eth3 --no-p4",
    ])

    run_in_kathara_machine(r3, commands=[
        "ip link set eth0 address 00:00:0a:00:00:0a",
        "ip link set eth1 address 00:00:0a:00:00:0d",
        "ip link set eth2 address 00:00:0a:00:00:0b",
        "ip link set eth3 address 00:00:0a:00:00:0c",
        "ethtool -K eth0 rx off tx off",
        "ethtool -K eth1 rx off tx off",
        "ethtool -K eth3 rx off tx off",
        "ethtool -K eth4 rx off tx off",
        "simple_switch_grpc -i 1@eth0 -i 2@eth3 -i 3@eth4 -i 4@eth1 --no-p4",
    ])

    run_in_kathara_machine(r4, commands=[
        "ip link set eth0 address 00:00:0a:00:00:0e",
        "ip link set eth1 address 00:00:0a:00:0f:01",
        "ethtool -K eth0 rx off tx off",
        "ethtool -K eth1 rx off tx off",
        "simple_switch_grpc -i 1@eth0 -i 2@eth1 --no-p4",
    ])

    # os.system("ethtool -K k8sveth_h rx off tx off")

    for r in (r1, r2, r3, r4):
        execute_simple_switch_cmds(r.name)

    cutils.copy_to_container(
        w2.container_id,
        '/home/flok3n/develop/virtual/telemetry2/int-platforms/platforms/bmv2-mininet/int.p4app/utils/int_collector_logging.py',
        '/int_collector_logging.py'
    )
    cutils.copy_to_container(
        w1.container_id, '/home/flok3n/develop/virtual/ubuntu20/src/examples/k8s/sr-job/sender_tcp.py', '/sender_tcp.py')
    cutils.copy_to_container(
        w1.container_id, '/home/flok3n/develop/virtual/ubuntu20/src/examples/k8s/sr-job/sender.py', '/sender.py')
    cutils.copy_to_container(
        w3.container_id, '/home/flok3n/develop/virtual/ubuntu20/src/examples/k8s/sr-job/receiver_tcp.py', '/receiver_tcp.py')
    cutils.copy_to_container(
        w3.container_id, '/home/flok3n/develop/virtual/ubuntu20/src/examples/k8s/sr-job/receiver.py', '/receiver.py')
    cutils.copy_to_container(
        container_id(extern), '/home/flok3n/develop/virtual/ubuntu20/src/examples/k8s/sr-job/sender_tcp_from_extern.py', '/sender_tcp.py')
    cutils.docker_exec_detached(
        w1.container_id, "ip", "link", "set", "dev", "eth10k", "mtu", "1000")
    cutils.docker_exec_detached(
        w2.container_id, 'mkdir', '-p', '/tmp/p4app_logs')
    os.system(f"kubectl label node {w1.internal_node_name} hosting=node")
    os.system(f"kubectl label node {w3.internal_node_name} hosting=redis")

    for node in (w1, w2, w3, c1):
        os.system(
            f"kubectl label node {node.internal_node_name} sname={node.name}")
        os.system(
            f"kubectl label node {node.internal_node_name} clustername={node.internal_node_name}")

    print('press enter to terminate cluster')
