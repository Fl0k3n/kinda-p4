import atexit
import re

from core.K8sNode import K8sNode


# replaces node name templates (e.g. { w1 }) to node names assigned by kind in all given files
# after program exits original names are restored, program must terminate normally (not killed)
def update_node_names_in_files(k8s_nodes: dict[str, K8sNode], *file_paths):
    pattern = re.compile(r'\{(.+?)\}')
    original_contents = {}

    def restore_file_content():
        for path, content in original_contents.items():
            with open(path, 'w') as f:
                f.write(content)

    atexit.register(restore_file_content)

    for file_path in file_paths:
        with open(file_path, 'r') as f:
            content = f.read()
        original_contents[file_path] = content
        new_content = ''
        last_start = 0
        for match in pattern.finditer(content):
            node_name = match.group(1).strip()
            if node_name in k8s_nodes:
                node = k8s_nodes[node_name]
                start = match.start()
                new_content += content[last_start:start]
                last_start = match.end()
                new_content += node.internal_node_name
        new_content += content[last_start:]
        with open(file_path, 'w') as f:
            f.write(new_content)
