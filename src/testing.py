# from Kathara.model.Lab import Lab

# from KatharaBackedNet import KatharaBackedCluster, container_id
# from util.iputils import NetIface
# from util.p4 import P4Params

# LAB_PATH = './examples/nets/fat_tree/kathara-data_center-fat_tree_base'


# with KatharaBackedCluster.from_file_system('test-cluster', LAB_PATH) as cluster:
#     for i in range(4):
#         cluster.add_worker(f'w{i + 1}')
#     cluster.add_control('c1')

#     cluster.connect_with_container('w1', node_iface=NetIface('eth10k', '201.1.1.2', 24), container_id=container_id(
#         'leaf_1_0_1'), container_iface=NetIface('eth2', '201.1.1.1', 24))
#     cluster.connect_with_container('w2', node_iface=NetIface('eth11k', '201.1.2.2', 24), container_id=container_id(
#         'leaf_1_0_1'), container_iface=NetIface('eth3', '201.1.2.1', 24))

#     cluster.connect_with_container('w3', node_iface=NetIface('eth12k', '201.2.1.2', 24), container_id=container_id(
#         'leaf_1_0_2'), container_iface=NetIface('eth2', '201.2.1.1', 24))
#     cluster.connect_with_container('w4', node_iface=NetIface('eth13k', '201.2.2.2', 24), container_id=container_id(
#         'leaf_1_0_2'), container_iface=NetIface('eth3', '201.2.2.1', 24))

#     # cluster.connect_with_container('w5', node_iface=NetIface('eth14k', '202.1.1.2', 24), container_id=container_id(
#     #     'leaf_2_0_1'), container_iface=NetIface('eth2', '202.1.1.1', 24))
#     # cluster.connect_with_container('w6', node_iface=NetIface('eth15k', '202.1.2.2', 24), container_id=container_id(
#     #     'leaf_2_0_1'), container_iface=NetIface('eth3', '202.1.2.1', 24))

#     # cluster.connect_with_container('w7', node_iface=NetIface('eth16k', '202.2.1.2', 24), container_id=container_id(
#     #     'leaf_2_0_2'), container_iface=NetIface('eth2', '201.2.1.1', 24))
#     # cluster.connect_with_container('w8', node_iface=NetIface('eth17k', '202.2.2.2', 24), container_id=container_id(
#     #     'leaf_2_0_2'), container_iface=NetIface('eth3', '202.2.2.1', 24))

#     cluster.connect_with_container('c1', node_iface=NetIface('eth18k', '202.2.2.2', 24), container_id=container_id(
#         'leaf_2_0_2'), container_iface=NetIface('eth3', '202.2.2.1', 24))

#     cluster.build()
#     print('DEBUG')

from Kathara.model.Lab import Lab

from KatharaBackedNet import KatharaBackedCluster, container_id
from util.iputils import NetIface
from util.p4 import P4Params

network = Lab("test1")

r1 = network.get_or_new_machine('r1')
network.connect_machine_to_link(r1.name, 'A')

r1.update_meta(args={
    "image": "kathara/base",
    "exec_commands": [
        "ifconfig eth0 10.10.3.1/24 up",
        "route add -net 10.10.1.0/24 gw 10.10.3.2 dev eth0",
        "route add -net 10.10.2.0/24 gw 10.10.3.2 dev eth0",
        "route add -net 10.10.4.0/24 gw 10.10.3.2 dev eth0",
        # "ip route add default via 10.10.1.2"
    ]
})

r2 = network.get_or_new_machine('r2')
network.connect_machine_to_link(r2.name, 'A')
network.connect_machine_to_link(r2.name, 'C')

r2.update_meta(args={
    "image": "kathara/base",
    "exec_commands": [
        "ifconfig eth0 10.10.3.2/24 up",
        "ifconfig eth1 10.10.4.1/24 up",
        "route add -net 10.10.0.0/24 gw 10.10.3.1 dev eth0",
        "route add -net 10.10.2.0/24 gw 10.10.4.2 dev eth1",
    ]
})

r3 = network.get_or_new_machine('r3')
network.connect_machine_to_link(r3.name, 'C')

r3.update_meta(args={
    "image": "kathara/base",
    "exec_commands": [
        "ifconfig eth0 10.10.4.2/24 up",
        "route add -net 10.10.0.0/24 gw 10.10.4.1 dev eth0",
        "route add -net 10.10.1.0/24 gw 10.10.4.1 dev eth0",
        "route add -net 10.10.3.0/24 gw 10.10.4.1 dev eth0",
    ]
})

with KatharaBackedCluster('test-cluster', network) as cluster:
    # cluster.enable_internet_access_via(container_id(r2))

    cluster.add_worker('w1', with_p4_nic=False, p4_params=P4Params(
        initial_compiled_script_host_path='./examples/p4/basic_arp_compiled.json', run_nic=True))
    cluster.add_worker('w2', with_p4_nic=False, p4_params=P4Params(
        initial_compiled_script_host_path='./examples/p4/basic_arp_compiled.json', run_nic=True))
    cluster.add_control('c1', with_p4_nic=False)

    cluster.connect_with_container(
        'w1',
        node_iface=NetIface('eth10k', '10.10.0.2', 24),
        container_id=container_id(r1),
        container_iface=NetIface('eth10c', '10.10.0.1', 24)
    )

    cluster.connect_with_container(
        'w2',
        node_iface=NetIface('eth11k', '10.10.1.2', 24),
        container_id=container_id(r2),
        container_iface=NetIface('eth11c', '10.10.1.1', 24)
    )

    cluster.connect_with_container(
        'c1',
        node_iface=NetIface('eth12k', '10.10.2.2', 24),
        container_id=container_id(r3),
        container_iface=NetIface('eth12c', '10.10.2.1', 24)
    )

    cluster.build()
    print("DEBUG")
    # input('press enter to terminate cluster')
