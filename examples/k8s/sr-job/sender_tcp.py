import socket
import sys
import time


def log(text):
    print(text, flush=True)


def sender():
    # Create a TCP/IP socket
    i = 0
    if len(sys.argv) < 3:
        receiver_address = ('10.10.4.2', 8959)
    else:
        receiver_address = (sys.argv[1], int(sys.argv[2]))

    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sender_address = ('', 4607)  # Empty string for localhost

        sock.bind(sender_address)
        # Connect the socket to the receiver's address and port
        log('Connecting to {} port {}'.format(*receiver_address))
        try:
            sock.connect(receiver_address)
            # Send data
            message = 'a' * 50
            log('Sending...')
            sock.sendall(message.encode())
            log('Sent')
        except Exception as e:
            log(f'Failed to send {i}: {e}')
        finally:
            sock.close()
            time.sleep(3)
            i += 1


if __name__ == "__main__":
    sender()
