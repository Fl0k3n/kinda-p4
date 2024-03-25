import os

from Kathara.manager.Kathara import Kathara
from Kathara.model.Lab import Lab as KatharaLab
from Kathara.model.Machine import Machine as KatharaMachine
from Kathara.parser.netkit.LabParser import LabParser

from core.ClusterBuilder import ClusterBuilder
from core.InternetAccessManager import InternetAccessManager
from core.NodeInitializer import NodeInitializer


class KatharaBackedCluster:
    LAB_NAME = 'default_lab'

    def __init__(self, cluster_name: str, kathara_lab: KatharaLab) -> None:
        self.cluster_builder = ClusterBuilder(
            cluster_name, NodeInitializer(), InternetAccessManager())
        self.kathara_lab = kathara_lab

    @classmethod
    def from_file_system(cls, cluster_name: str, kathara_lab_path: str) -> 'KatharaBackedCluster':
        lab = LabParser().parse(kathara_lab_path)
        lab.name = cls.LAB_NAME
        return KatharaBackedCluster(cluster_name, lab)

    def __enter__(self) -> ClusterBuilder:
        print('Deploying Kathara lab...')
        cluster = self._setup(first_try=True)
        print('Kathara lab ready')
        return cluster

    def __exit__(self, *args):
        self._cleanup()

    def _setup(self, first_try: bool) -> ClusterBuilder:
        try:
            Kathara.get_instance().deploy_lab(self.kathara_lab)
            return self.cluster_builder
        except:
            if first_try:
                self._cleanup()
            else:
                raise

            return self._setup(first_try=False)

    def _cleanup(self):
        self.cluster_builder.destroy()
        Kathara.get_instance().undeploy_lab(lab_name=self.kathara_lab.name)
        Kathara.get_instance().wipe()


# deprecated
def container_id(machine: KatharaMachine | str) -> str:
    if isinstance(machine, KatharaMachine):
        return machine.api_object.id
    return Kathara.get_instance().get_machine_api_object(machine, lab_name=KatharaBackedCluster.LAB_NAME).id


def run_in_kathara_machine(machine: KatharaMachine | str, commands: list[str]):
    cid = container_id(machine)
    for cmd in commands:
        os.system(f'sudo docker exec -d {cid} {cmd}')
