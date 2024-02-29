import socket
import sys


def log(text):
    print(text, flush=True)


def receiver():
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind the socket to the address and port
    if len(sys.argv) < 2:
        server_address = ('0.0.0.0', 8959)
    else:
        server_address = ('0.0.0.0', int(sys.argv[1]))

    log('Starting up on {} port {}'.format(*server_address))
    sock.bind(server_address)

    while True:
        # Wait for a message
        log('Waiting for a message...')
        data, address = sock.recvfrom(4096)

        # Print the received message
        log('Received: ' + data.decode())


if __name__ == "__main__":
    receiver()
