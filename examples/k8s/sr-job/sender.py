import socket
import sys


def log(text):
    print(text, flush=True)


def sender():
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Sender address and port
    sender_address = ('', 4607)  # Empty string for localhost

    # Receiver address and port
    if len(sys.argv) < 3:
        receiver_address = ('10.10.3.2', 8959)
    else:
        receiver_address = (sys.argv[1], int(sys.argv[2]))

    log('sending to ' + str(receiver_address))
    # Message to send
    message = "Hello, receiver! This is a test message."

    try:
        # Bind socket to the sender address and port
        sock.bind(sender_address)

        # Send data
        log('Sending: ' + message)
        sock.sendto(message.encode(), receiver_address)

    finally:
        # Close the socket
        log('Closing socket')
        sock.close()


if __name__ == "__main__":
    sender()
