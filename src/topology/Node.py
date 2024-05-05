from abc import ABC, abstractmethod
from enum import Enum
from typing import NamedTuple, Optional


class NodeType(Enum):
    K8S = "node"
    HOST = "host"
    INC_SWITCH = "inc-switch"
    NET = "net"
    EXTERNAL = "external"


PeerNameToIpMac = dict[str, tuple[str, str]]


class NodeMeta(ABC):
    @abstractmethod
    def get_type(self) -> NodeType:
        pass

    def _assert_device_type(self, expected: NodeType):
        assert self.get_type() == expected, \
            f'Expected type {str(expected.value)}'

    def k8s_meta(self) -> "K8sNodeMeta":
        self._assert_device_type(NodeType.K8S)
        return self

    def host_meta(self) -> "HostMeta":
        self._assert_device_type(NodeType.HOST)
        return self

    def simple_host_meta(self) -> "SimpleHostMeta":
        assert self.get_type() in (NodeType.HOST, NodeType.EXTERNAL)
        return self

    def inc_switch_meta(self) -> "IncSwitchMeta":
        self._assert_device_type(NodeType.INC_SWITCH)
        return self

    def net_device_meta(self) -> "NetDeviceMeta":
        self._assert_device_type(NodeType.NET)
        return self

    def external_device_meta(self) -> "ExternalDeviceMeta":
        self._assert_device_type(NodeType.EXTERNAL)
        return self


class LinkConfig(NamedTuple):
    peer_name: str
    masked_ip: str
    mac: str


class NodeConfig(NamedTuple):
    name: str
    meta: NodeMeta
    links: list[LinkConfig]


class K8sNodeMeta(NodeMeta):
    def __init__(self, control_plane: bool) -> None:
        self.control_plane = control_plane

    @staticmethod
    def Worker() -> "K8sNodeMeta":
        return K8sNodeMeta(control_plane=False)

    @staticmethod
    def Control() -> "K8sNodeMeta":
        return K8sNodeMeta(control_plane=True)

    def get_type(self) -> NodeType:
        return NodeType.K8S


FORWARD_PROGRAM = "forward"
TELEMETRY_PROGRAM = "telemetry"


class IncSwitchMeta(NodeMeta):
    GRPC_PORT_COUNTER = 0
    GRPC_LOCAL_BASE_PORT = 9560
    COMMAND = "simple_switch_grpc"

    def __init__(self, image="flok3n/p4c-epoch_thrift:latest", program: str = TELEMETRY_PROGRAM, open_grpc=True,
                 grpc_port: Optional[int] = None, grpc_internal_port=9559, start_program=False,
                 startup_commands: list[str] = None, simple_switch_cli_commands: list[str] = None) -> None:
        self.image = image
        self.program = program
        self.start_program = start_program
        self.open_grpc = open_grpc
        self.grpc_internal_port = grpc_internal_port
        self.simple_switch_cli_commands = simple_switch_cli_commands
        if open_grpc and grpc_port is None:
            self.grpc_port = IncSwitchMeta.GRPC_LOCAL_BASE_PORT + \
                IncSwitchMeta.GRPC_PORT_COUNTER
            IncSwitchMeta.GRPC_PORT_COUNTER += 1
        else:
            self.grpc_port = grpc_port
        self.startup_commands = startup_commands if startup_commands is not None else []
        if self.simple_switch_cli_commands:
            self.startup_commands.extend(self.simple_switch_cli_commands)

    def get_run_command(self, iface_names: list[str]) -> str:
        cmd = self.COMMAND
        for i, iface in enumerate(iface_names):
            cmd += f" -i {i+1}@{iface}"
        cmd += f' {self.program}' if self.start_program else ' --no-p4'
        return cmd

    def get_type(self) -> NodeType:
        return NodeType.INC_SWITCH


class NetDeviceMeta(NodeMeta):
    def get_type(self) -> NodeType:
        return NodeType.NET


class SimpleHostMeta(NodeMeta):
    def __init__(self, default_route_via: str = None, mtu: int = None,
                 image="kathara/base", startup_commands: list[str] = None) -> None:
        self.image = image
        self.startup_commands = startup_commands if startup_commands is not None else []
        self.default_route_via = default_route_via
        self.mtu = None


class ExternalDeviceMeta(SimpleHostMeta):
    def get_type(self) -> NodeType:
        return NodeType.EXTERNAL


class HostMeta(SimpleHostMeta):
    def get_type(self) -> NodeType:
        return NodeType.HOST
