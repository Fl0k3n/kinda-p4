from Kathara.manager.Kathara import Kathara
from Kathara.model.Lab import Lab as KatharaLab

from ClusterBuilder import ClusterBuilder


class KatharaBackedNet:
    def __init__(self, cluster_builder: ClusterBuilder, kathara_lab: KatharaLab) -> None:
        self.cluster_builder = cluster_builder
        self.kathara_lab = kathara_lab

    def __enter__(self):
        Kathara.get_instance().deploy_lab(self.kathara_lab)
        self.cluster_builder.build()

    def __exit__(self, *args):
        self.cluster_builder.destroy()
        Kathara.get_instance().undeploy_lab(lab_name=self.kathara_lab.name)
