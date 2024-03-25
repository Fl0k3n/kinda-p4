import os

from Kathara.manager.Kathara import Kathara
from Kathara.model.Machine import Machine as KatharaMachine


def container_id(machine: KatharaMachine | str, lab_name: str) -> str:
    if isinstance(machine, KatharaMachine):
        return machine.api_object.id
    return Kathara.get_instance().get_machine_api_object(machine, lab_name=lab_name).id


def simple_switch_CLI(*cmds: list[str]) -> list[str]:
    return [
        "echo '#!/bin/bash' >> s.sh",
        "echo 'while [[ $(pgrep simple_switch) -eq 0 ]]; do sleep 1; done' >> s.sh",
        "echo 'until simple_switch_CLI <<< 'help'; do sleep 1; done' >> s.sh",
        *[f"echo \"echo '{cmd}' | simple_switch_CLI\" >> s.sh" for cmd in cmds],
        "chmod u+x s.sh",
    ]


def execute_simple_switch_cmds(name):
    os.system("sudo docker ps | grep _" + name +
              "_ | awk '{print $1}' | xargs -I {} sudo docker exec {} ./s.sh")


def copy_file(path, container_name):
    name = os.path.basename(path)
    os.system("sudo docker ps | grep _" + container_name +
              "_ | awk '{print $1}' | xargs -I {} sudo docker cp " + path + " {}:" + name)


def run_in_container(name, command):
    os.system("sudo docker ps | grep _" + name +
              "_ | awk '{print $1}' | xargs -I {} sudo docker exec {} " + command)


def run_in_kathara_machine(machine: KatharaMachine | str, commands: list[str], lab_name: str):
    cid = container_id(machine, lab_name)
    for cmd in commands:
        os.system(f'sudo docker exec -d {cid} {cmd}')
