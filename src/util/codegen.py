class CodeGenHelper:
    def __init__(self, single_indent="    ") -> None:
        self.code: list[str] = []
        self._indent = 0
        self.single_indent = single_indent
        self._indent_checkpoints = []

    def indent(self):
        self._indent += 1

    def checkpoint_indent(self):
        self._indent_checkpoints.append(self._indent)

    def restore_checkpoint(self):
        self._indent = self._indent_checkpoints.pop()

    def unindent(self):
        self._indent -= 1

    def clear_indent(self):
        self._indent = 0

    def append(self, line: str):
        self.code.append((self.single_indent * self._indent) + line)

    def append_lines(self, *lines: str):
        for line in lines:
            self.append(line)

    def append_empty(self):
        self.code.append('')

    def merge(self, other: "CodeGenHelper"):
        self.code.extend(
            [(self.single_indent * self.indent) + line for line in other.code])

    def join(self) -> str:
        return "\n".join(self.code) + "\n"

    def join_indented(self, indent: int) -> str:
        return "\n".join([(self.single_indent * indent) + line for line in self.code])
