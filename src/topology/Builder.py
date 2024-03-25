from abc import ABC, abstractmethod

from Kathara.model.Lab import Lab as KatharaLab

from core.ClusterBuilder import ClusterBuilder
from topology.Node import NodeConfig


class TopologyBuilder(ABC):
    @abstractmethod
    def setup_network(self, network: KatharaLab):
        pass

    @abstractmethod
    def attach_and_build_cluster(self, network: KatharaLab, ClusterBuilder: ClusterBuilder):
        pass

    @abstractmethod
    def get_devices(self) -> list[NodeConfig]:
        pass
