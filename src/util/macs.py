from typing import Generator


def mac_generator(start_mac="00:00:0a:00:00:00") -> Generator[str, None, None]:
    cur_mac = [int(b, base=16) for b in start_mac.split(':')]
    while True:
        yield ":".join([hex(b)[2:].zfill(2) for b in cur_mac])
        for i in range(5, -1, -1):
            if cur_mac[i] < 255:
                cur_mac[i] += 1
                break
            else:
                cur_mac[i] = 0
