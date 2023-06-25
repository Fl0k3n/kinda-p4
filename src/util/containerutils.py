import subprocess as sp


def get_container_pid(container_id: str) -> str:
    output = sp.run(['sudo', 'docker', 'inspect', '-f', '{{.State.Pid}}', container_id],
                    capture_output=True, text=True)
    return output.stdout.strip()


def create_namespace_name(container_pid: str) -> str:
    return f'ns_{container_pid}'


def attach_netns_to_host(container_pid: str, netns_name: str):
    res = sp.run(['sudo', 'ip', 'netns', 'attach', netns_name,
                 container_pid], capture_output=True, text=True)
    assert res.returncode == 0, f'Failed to attach namespace: {netns_name} to host'


def docker_exec_it(container_id: str, *commands: list[str]) -> sp.CompletedProcess[str]:
    return sp.run(['sudo', 'docker', 'exec', '-it', container_id, *commands], text=True,
                  capture_output=True)


def docker_exec_detached(container_id: str, *commands: list[str]):
    return sp.run(['sudo', 'docker', 'exec', '-d', container_id, *commands], text=True, capture_output=True)


def is_process_running(container_id: str, proc_name: str) -> bool:
    # TODO smth more reliable
    return docker_exec_it(container_id, 'pidof', proc_name).returncode == 0


def docker_ps() -> str:
    return sp.run(['sudo', 'docker', 'ps'], capture_output=True, text=True).stdout


def copy_to_container(container_id: str, host_path: str, container_path: str):
    sp.run(['sudo', 'docker', 'cp', host_path,
           f'{container_id}:{container_path}'], capture_output=True, text=True)


def turn_off_tcp_checksum_offloading(container_id: str, iface_name: str):
    docker_exec_detached(container_id, 'ethtool', '-K',
                         iface_name, 'rx', 'off', 'tx', 'off')


def copy_and_run_script_in_container(container_id: str, script_host_path: str, script_container_path: str):
    copy_to_container(container_id, script_host_path, script_container_path)
    docker_exec_it(container_id, script_container_path)
