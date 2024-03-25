from util.iputils import Cidr

POD_CIDR = Cidr("10.244.0.0", 16)
TUN_CIDR = Cidr("192.168.0.0", 16)
KIND_CIDR = Cidr("172.0.0.0", 8)
