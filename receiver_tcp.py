import socket


def receiver():
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the socket to the address and port
    server_address = ('0.0.0.0', 8959)
    print('Starting up on {} port {}'.format(*server_address))
    sock.bind(server_address)

    # Listen for incoming connections
    sock.listen(1)

    while True:
        # Wait for a connection
        print('Waiting for a connection...')
        connection, client_address = sock.accept()

        try:
            print('Connection from', client_address)

            # Receive the data in small chunks and reassemble it
            data = b''
            while True:
                chunk = connection.recv(16)
                if not chunk:
                    break
                data += chunk

            if data:
                # Print the received message
                print('Received:', data.decode())

        finally:
            # Clean up the connection
            connection.close()


if __name__ == "__main__":
    receiver()
