from Kathara.manager.Kathara import Kathara
from Kathara.model.Lab import Lab as KatharaLab
from Kathara.model.Machine import Machine as KatharaMachine

from ClusterBuilder import ClusterBuilder
from InternetAccessManager import InternetAccessManager
from NodeInitializer import NodeInitializer


class KatharaBackedCluster:
    def __init__(self, cluster_name: str, kathara_lab: KatharaLab) -> None:
        self.cluster_builder = ClusterBuilder(
            cluster_name, NodeInitializer(), InternetAccessManager())
        self.kathara_lab = kathara_lab

    def __enter__(self) -> ClusterBuilder:
        return self._setup(first_try=True)

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


def container_id(machine: KatharaMachine) -> str:
    return machine.api_object.id
