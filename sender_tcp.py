import socket


def sender():
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sender_address = ('', 4607)  # Empty string for localhost

    sock.bind(sender_address)
    # Connect the socket to the receiver's address and port
    receiver_address = ('10.10.3.2', 8959)
    print('Connecting to {} port {}'.format(*receiver_address))
    sock.connect(receiver_address)

    try:
        # Send data
        message = "Hello, receiver! This is a test message."
        print('Sending:', message)
        sock.sendall(message.encode())

    finally:
        # Close the socket
        print('Closing socket')
        sock.close()


if __name__ == "__main__":
    sender()
