#!/bin/bash

. /etc/os-release
echo "deb https://download.opensuse.org/repositories/home:/p4lang/xUbuntu_${VERSION_ID}/ /" | tee /etc/apt/sources.list.d/home:p4lang.list
curl -L "https://download.opensuse.org/repositories/home:/p4lang/xUbuntu_${VERSION_ID}/Release.key" | apt-key add -
apt update
apt install p4lang-p4c

# p4c-bm2-ss --p4v 16 -o test.json test.p4

# simple_switch --log-console --dump-packet-data 64 -i 0@veth0 test.json

# simple_switch_CLI example
# table_add MyIngress.ipv4_lpm MyIngress.ipv4_forward 10.0.2.2/32 => 08:00:00:00:03:00 3
# table_add MyIngress.myTunnel_exact MyIngress.myTunnel_forward 2 => 2

