from KatharaBackedNet import KatharaBackedCluster, container_id
from util.iputils import NetIface

LAB_PATH = './examples/nets/fat_tree/kathara-data_center-fat_tree_base'


with KatharaBackedCluster.from_file_system('test-cluster', LAB_PATH) as cluster:
    for i in range(8):
        cluster.add_worker(f'w{i + 1}')
    cluster.add_control('c1')

    cluster.connect_with_container('w1', node_iface=NetIface('eth10k', '201.1.1.2', 24), container_id=container_id(
        'leaf_1_0_1'), container_iface=NetIface('eth2', '201.1.1.1', 24))
    cluster.connect_with_container('w2', node_iface=NetIface('eth11k', '201.1.2.2', 24), container_id=container_id(
        'leaf_1_0_1'), container_iface=NetIface('eth3', '201.1.2.1', 24))

    cluster.connect_with_container('w3', node_iface=NetIface('eth12k', '201.2.1.2', 24), container_id=container_id(
        'leaf_1_0_2'), container_iface=NetIface('eth2', '201.2.1.1', 24))
    cluster.connect_with_container('w4', node_iface=NetIface('eth13k', '201.2.2.2', 24), container_id=container_id(
        'leaf_1_0_2'), container_iface=NetIface('eth3', '201.2.2.1', 24))

    cluster.connect_with_container('w5', node_iface=NetIface('eth14k', '202.1.1.2', 24), container_id=container_id(
        'leaf_2_0_1'), container_iface=NetIface('eth2', '202.1.1.1', 24))
    cluster.connect_with_container('w6', node_iface=NetIface('eth15k', '202.1.2.2', 24), container_id=container_id(
        'leaf_2_0_1'), container_iface=NetIface('eth3', '202.1.2.1', 24))

    cluster.connect_with_container('w7', node_iface=NetIface('eth16k', '202.2.1.2', 24), container_id=container_id(
        'leaf_2_0_2'), container_iface=NetIface('eth2', '201.2.1.1', 24))
    cluster.connect_with_container('w8', node_iface=NetIface('eth17k', '202.2.2.2', 24), container_id=container_id(
        'leaf_2_0_2'), container_iface=NetIface('eth3', '202.2.2.1', 24))

    cluster.connect_with_container('c1', node_iface=NetIface('eth18k', '202.2.2.3', 24), container_id=container_id(
        'leaf_2_0_2'), container_iface=NetIface('eth3', '202.2.2.1', 24))

    cluster.build()
    input('press enter to terminate')
