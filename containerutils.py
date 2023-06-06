import subprocess as sp


def get_container_pid(container_id: str) -> str:
    output = sp.run(['sudo', 'docker', 'inspect', '-f', '{{.State.Pid}}', container_id],
                    capture_output=True, text=True)
    return output.stdout.strip()


def attach_netns_to_host(container_pid: str, netns_name: str):
    sp.run(['sudo', 'ip', 'netns', 'attach', netns_name, container_pid])


def docker_exec_it(container_id: str, *commands: list[str]) -> str:
    return sp.run(['sudo', 'docker', 'exec', '-it', container_id, *commands], text=True,
                  capture_output=True).stdout


def copy_and_run_script_in_container(container_id: str, script_host_path: str, script_container_path: str):
    sp.run(['sudo', 'docker', 'cp', script_host_path,
           f'{container_id}:{script_container_path}'])
    docker_exec_it(container_id, script_container_path)
