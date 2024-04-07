#!/bin/bash

apt update

apt install -y --no-install-recommends \
    iputils-ping \
    inetutils-traceroute \
    net-tools \
    tcpdump \
    dnsutils \
    vim
