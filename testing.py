from Kathara.manager.Kathara import Kathara
from Kathara.model.Lab import Lab

from ClusterBuilder import ClusterBuilder
from iputils import NetIface
from KatharaBackedNet import KatharaBackedCluster, container_id

lab = Lab("test1")

r1 = lab.get_or_new_machine('r1')
lab.connect_machine_to_link(r1.name, 'B')

r1.update_meta(args={
    "image": "kathara/base",
    "exec_commands": [
        "ifconfig eth0 10.10.1.1/24 up",
        "route add -net 10.10.2.0/24 gw 10.10.1.2 dev eth0"
    ]
})

r2 = lab.get_or_new_machine('r2')
lab.connect_machine_to_link(r2.name, 'B')

r2.update_meta(args={
    "image": "kathara/base",
    "exec_commands": [
        "ifconfig eth0 10.10.1.2/24 up",
        "route add -net 10.10.0.0/24 gw 10.10.1.1 dev eth0"
    ]
})

with KatharaBackedCluster('test-cluster', lab) as cb:
    cb.add_worker('w1', with_p4_nic=False)
    cb.add_control('c1', with_p4_nic=False)

    cb.connect_with_container('w1', NetIface(
        'eth10k', '10.10.2.2', 24), container_id(r2), NetIface('eth10c', '10.10.2.1', 24))
    cb.connect_with_container('c1', NetIface(
        'eth10k', '10.10.0.2', 24), container_id(r1), NetIface('eth10c', '10.10.0.1', 24))

    cb.build()
    print('DEBUG')

# cb.destroy()
# Kathara.get_instance().undeploy_lab(lab_name=lab.name)
