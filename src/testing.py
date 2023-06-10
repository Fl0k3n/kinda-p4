from Kathara.model.Lab import Lab

from KatharaBackedNet import KatharaBackedCluster, container_id
from util.iputils import NetIface
from util.p4 import P4Params

network = Lab("test1")

r1 = network.get_or_new_machine('r1')
network.connect_machine_to_link(r1.name, 'B')

r1.update_meta(args={
    "image": "kathara/base",
    "exec_commands": [
        "ifconfig eth0 10.10.1.1/24 up",
        "route add -net 10.10.2.0/24 gw 10.10.1.2 dev eth0",
        "ip route add default via 10.10.1.2"
    ]
})

r2 = network.get_or_new_machine('r2')
network.connect_machine_to_link(r2.name, 'B')

r2.update_meta(args={
    "image": "kathara/base",
    "exec_commands": [
        "ifconfig eth0 10.10.1.2/24 up",
        "route add -net 10.10.0.0/24 gw 10.10.1.1 dev eth0",
    ]
})

with KatharaBackedCluster('test-cluster', network) as cluster:
    cluster.enable_internet_access_via(container_id(r2))

    cluster.add_worker('w1', with_p4_nic=True, p4_params=P4Params(
        initial_compiled_script_host_path='./examples/p4/basic_arp_compiled.json', run_nic=True))
    cluster.add_worker('w2', with_p4_nic=False, p4_params=P4Params(
        initial_compiled_script_host_path='./examples/p4/basic_arp_compiled.json', run_nic=False))
    cluster.add_control('c1', with_p4_nic=False)

    cluster.connect_with_container(
        'w1',
        node_iface=NetIface('eth10k', '10.10.0.2', 24),
        container_id=container_id(r1),
        container_iface=NetIface('br_1c', '10.10.0.1', 24)
    )

    cluster.connect_with_container(
        'w2',
        node_iface=NetIface('eth10k', '10.10.2.3', 24),
        container_id=container_id(r2),
        container_iface=NetIface('br_2c', '10.10.2.1', 24)
    )

    cluster.connect_with_container(
        'c1',
        node_iface=NetIface('eth10k', '10.10.2.2', 24),
        container_id=container_id(r2),
        container_iface=NetIface('br_2c', '10.10.2.1', 24)
    )

    cluster.build()
    print('DEBUG')
