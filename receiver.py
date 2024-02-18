import socket


def receiver():
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind the socket to the address and port
    server_address = ('0.0.0.0', 8959)
    print('Starting up on {} port {}'.format(*server_address))
    sock.bind(server_address)

    while True:
        # Wait for a message
        print('Waiting for a message...')
        data, address = sock.recvfrom(4096)

        # Print the received message
        print('Received:', data.decode())


if __name__ == "__main__":
    receiver()
