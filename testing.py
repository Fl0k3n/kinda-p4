from Kathara.manager.Kathara import Kathara
from Kathara.model.Lab import Lab

from ClusterBuilder import ClusterBuilder

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

cb = ClusterBuilder('test-cluster')
cb.add_worker('w1', '10.10.2.2', 24, with_p4_nic=False)
cb.add_control('c1', '10.10.0.2', 24)

cb.build()
Kathara.get_instance().deploy_lab(lab)

cb.connect_with_container('w1', r2.api_object.id, '10.10.2.1')
cb.connect_with_container('c1', r1.api_object.id, '10.10.0.1')

cb.destroy()
Kathara.get_instance().undeploy_lab(lab_name=lab.name)
