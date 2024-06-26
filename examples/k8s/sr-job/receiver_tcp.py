import socket
import sys


def log(text):
    print(text, flush=True)


def receiver():
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the socket to the address and port
    if len(sys.argv) < 2:
        server_address = ('0.0.0.0', 8959)
    else:
        server_address = ('0.0.0.0', int(sys.argv[1]))
    log('Starting up on {} port {}'.format(*server_address))
    sock.bind(server_address)

    # Listen for incoming connections
    sock.listen(1)
    i = 0
    while True:
        # Wait for a connection
        log('Waiting for a connection...')
        connection, client_address = sock.accept()

        try:
            log(f'{i}: Connection from ' + str(client_address))

            # Receive the data in small chunks and reassemble it
            data = b''
            while True:
                chunk = connection.recv(16)
                if not chunk:
                    break
                data += chunk

            if data:
                # Print the received message
                log('Received message of length' + str(len(data.decode())))
        except Exception as e:
            log(f'{i}: failed to receive: {e}')
        finally:
            # Clean up the connection
            connection.close()


if __name__ == "__main__":
    print('starting receiver', flush=True)
    receiver()
