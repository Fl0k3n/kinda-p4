import os

from Kathara.model.Lab import Lab

import util.containerutils as cutils
from net.KatharaBackedNet import (KatharaBackedCluster, container_id,
                                  run_in_kathara_machine)
from net.util import execute_simple_switch_cmds, simple_switch_CLI
from util.iputils import NetIface

network = Lab("test1")

r1 = network.get_or_new_machine('r1')
network.connect_machine_to_link(r1.name, 'A')

r1.update_meta(args={
    "image": "flok3n/p4c-epoch_thrift:latest",
    "exec_commands": [
        *simple_switch_CLI(
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.0.2/32 => 00:00:0a:00:00:06 00:00:0a:00:00:01 2',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.2.0/24 => 00:00:0a:00:00:05 00:00:0a:00:00:07 1',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.3.0/24 => 00:00:0a:00:00:05 00:00:0a:00:00:07 1',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.4.0/24 => 00:00:0a:00:00:05 00:00:0a:00:00:07 1',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.5.0/24 => 00:00:0a:00:00:05 00:00:0a:00:00:07 1',
            'table_add ingress.Forward.arp_exact ingress.Forward.reply_arp 10.10.0.1 => 00:00:0a:00:00:06',
            # 'table_add tb_activate_source activate_source 2 =>',
            # 'table_add tb_int_source configure_source 10.10.0.2&&&0xFFFFFFFF 10.10.4.2&&&0xFFFFFFFF 0x11FF&&&0xFFFF 0x22FF&&&0xFFFF => 4 10 8 0xFF00 0',
            # # 'table_add tb_int_source configure_source 10.10.0.2&&&0xFFFFFFFF 10.10.4.2&&&0xFFFFFFFF 0x0&&&0x0 0x18EB&&&0xFFFF => 4 10 8 0xFF00 0',
            # 'table_add tb_int_transit configure_transit 0.0.0.0/0 => 1 1500',
        ),
    ]
})

r2 = network.get_or_new_machine('r2')
network.connect_machine_to_link(r2.name, 'A')
network.connect_machine_to_link(r2.name, 'B')

r2.update_meta(args={
    "image": "flok3n/p4c-epoch_thrift:latest",
    "exec_commands": [
        *simple_switch_CLI(
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.2.2/32 => 00:00:0a:00:00:09 00:00:0a:00:00:02 3',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.0.0/24 => 00:00:0a:00:00:07 00:00:0a:00:00:05 1',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.4.0/24 => 00:00:0a:00:00:08 00:00:0a:00:00:0a 2',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.5.0/24 => 00:00:0a:00:00:08 00:00:0a:00:00:0a 2',
            'table_add ingress.Forward.arp_exact ingress.Forward.reply_arp 10.10.2.1 => 00:00:0a:00:00:09',
            # 'table_add tb_int_transit configure_transit 0.0.0.0/0 => 2 1500',
        ),
    ]
})

r3 = network.get_or_new_machine('r3')
network.connect_machine_to_link(r3.name, 'B')
r3.update_meta(args={
    "image": "flok3n/p4c-epoch_thrift:latest",
    "exec_commands": [
        *simple_switch_CLI(
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.4.2/32 => 00:00:0a:00:00:0b 00:00:0a:00:00:03 2',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.5.2/32 => 00:00:0a:00:00:0c 00:00:0a:00:00:04 3',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.0.0/24 => 00:00:0a:00:00:0a 00:00:0a:00:00:08 1',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.1.0/24 => 00:00:0a:00:00:0a 00:00:0a:00:00:08 1',
            'table_add ingress.Forward.ipv4_lpm ingress.Forward.ipv4_forward 10.10.2.0/24 => 00:00:0a:00:00:0a 00:00:0a:00:00:08 1',
            'table_add ingress.Forward.arp_exact ingress.Forward.reply_arp 10.10.4.1 => 00:00:0a:00:00:0b',
            'table_add ingress.Forward.arp_exact ingress.Forward.reply_arp 10.10.5.1 => 00:00:0a:00:00:0c',
            # 'table_add tb_int_sink configure_sink 2 => 1',
            # 'mirroring_add 1 1',
            # 'table_add tb_int_reporting send_report 0.0.0.0/0 => 00:00:0a:00:00:0a 10.10.3.2 00:00:0a:00:00:08 10.10.2.2 6000',
            # 'table_add tb_int_transit configure_transit 0.0.0.0/0 => 3 1500',
        ),
    ]
})

with KatharaBackedCluster('test-cluster', network) as cluster:
    w1 = cluster.add_worker('w1')
    w2 = cluster.add_worker('w2')
    w3 = cluster.add_worker('w3')
    cluster.add_control('c1')

    cluster.connect_with_container(
        'w1',
        node_iface=NetIface('eth10k', '10.10.0.2', 24,
                            mac="00:00:0a:00:00:01"),
        container_id=container_id(r1),
        container_iface=NetIface('eth1', '10.10.0.1', 24)
    )

    cluster.connect_with_container(
        'w2',
        node_iface=NetIface('eth10k', '10.10.2.2', 24,
                            mac="00:00:0a:00:00:02"),
        container_id=container_id(r2),
        container_iface=NetIface('eth2', '10.10.2.1', 24)
    )

    cluster.connect_with_container(
        'w3',
        node_iface=NetIface('eth10k', '10.10.4.2', 24,
                            mac="00:00:0a:00:00:03"),
        container_id=container_id(r3),
        container_iface=NetIface('eth1', '10.10.4.1', 24)
    )

    cluster.connect_with_container(
        'c1',
        node_iface=NetIface('eth10k', '10.10.5.2', 24,
                            mac="00:00:0a:00:00:04"),
        container_id=container_id(r3),
        container_iface=NetIface('eth2', '10.10.5.1', 24)
    )

    cluster.build()

    run_in_kathara_machine(r1, commands=[
        "ip link set eth0 address 00:00:0a:00:00:05",
        "ip link set eth1 address 00:00:0a:00:00:06",
        "simple_switch -i 1@eth0 -i 2@eth1 int.json",
    ])

    run_in_kathara_machine(r2, commands=[
        "ip link set eth0 address 00:00:0a:00:00:07",
        "ip link set eth1 address 00:00:0a:00:00:08",
        "ip link set eth2 address 00:00:0a:00:00:09",
        "simple_switch -i 1@eth0 -i 2@eth1 -i 3@eth2 int.json",
    ])

    run_in_kathara_machine(r3, commands=[
        "ip link set eth0 address 00:00:0a:00:00:0a",
        "ip link set eth1 address 00:00:0a:00:00:0b",
        "ip link set eth2 address 00:00:0a:00:00:0c",
        "simple_switch -i 1@eth0 -i 2@eth1 -i 3@eth2 int.json",
    ])

    for r in (r1, r2, r3):
        execute_simple_switch_cmds(r.name)

    # uncomment if you want to test tcp or udp communication
    # go to the w1 and w3 nodes (kinda w1 bash, kinda w3 bash), see README for cli
    # then on w3 run: python3 receiver.py
    # and on w1 run: python3 sender.py
    # if all went fine you should see some logs on those nodes

    # path_to_examples = "/home/flok3n/develop/virtual/ubuntu20"  # TODO set project path
    # cutils.copy_to_container(
    #     w1.container_id, f'{path_to_examples}/src/examples/k8s/sr-job/sender_tcp.py', '/sender_tcp.py')
    # cutils.copy_to_container(
    #     w1.container_id, f'{path_to_examples}/src/examples/k8s/sr-job/sender.py', '/sender.py')
    # cutils.copy_to_container(
    #     w3.container_id, f'{path_to_examples}/src/examples/k8s/sr-job/receiver_tcp.py', '/receiver_tcp.py')
    # cutils.copy_to_container(
    #     w3.container_id, f'{path_to_examples}/examples/k8s/sr-job/receiver.py', '/receiver.py')

    # not 100% sure why this mtu is set and why to that value, probably just to be safe because P4 app inspects those packets and they are encapsulated in GRE
    cutils.docker_exec_detached(
        w1.container_id, "ip", "link", "set", "dev", "eth10k", "mtu", "1000")

    # if you want to test some simple deployment see examples/k8s/multiple-svcs (see README)
    # labeling is used to make sure that pods end up on nodes that we want
    # after you run this you should get node ip (any node in the cluster), e.g. run
    # docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <container id>
    # then go to ip:30007 in the browser, you should see that 1. it works 2. it stores some timestamps (that are saved in redis)
    # meaning that pods can communicate.
    #
    # To verify that they indeed communicate through the virtual cluster and not through host you can see wireshark, find some
    # kathara interface (try more than 1 if you don' see any HTTP traffic), you should see that http is encapsulated in GRE, you should also verify ip addresses.
    os.system(f"kubectl label node {w1.internal_node_name} hosting=node")
    os.system(f"kubectl label node {w3.internal_node_name} hosting=redis")

    # this confing uses telemetry P4 app but it doesn't configure sending those telemetry logs. see other files like qos_eval_topo. This is partially configured by kinda-sdn.

    print('press enter to terminate cluster')
