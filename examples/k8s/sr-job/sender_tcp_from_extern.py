import socket
import sys


def log(text):
    print(text, flush=True)


def sender():
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # sender_address = ('', 4607)  # Empty string for localhost

    # sock.bind(sender_address)
    # Connect the socket to the receiver's address and port
    if len(sys.argv) < 3:
        receiver_address = ('10.10.4.2', 30008)
    else:
        receiver_address = (sys.argv[1], int(sys.argv[2]))
    log('Connecting to {} port {}'.format(*receiver_address))
    sock.connect(receiver_address)

    try:
        # Send data
        message = 'a' * 50
        log('Sending: ' + message)
        sock.sendall(message.encode())

    finally:
        # Close the socket
        log('Closing socket')
        sock.close()


if __name__ == "__main__":
    sender()
