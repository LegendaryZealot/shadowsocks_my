from __future__ import with_statement
import sys
import socket
import select
import SocketServer
import struct
import os
import logging


def send_all(sock, data):
    bytes_sent = 0
    while True:
        r = sock.send(data[bytes_sent:])
        if r < 0:
            return r
        bytes_sent += r
        if bytes_sent == len(data):
            return bytes_sent


# class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
#     allow_reuse_address = True
class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True


class Socks5Server(SocketServer.StreamRequestHandler):

    def handle_tcp(self, sock, remote):
        try:
            fdset = [sock, remote]
            while True:
                r, w, e = select.select(fdset, [], [])
                if sock in r:
                    data = self.encrypt(sock.recv(4096))
                    if len(data) <= 0:
                        break
                    result = send_all(remote, data)
                    if result < len(data):
                        raise Exception('failed to send all data')

                if remote in r:
                    data = self.decrypt(remote.recv(4096))
                    if len(data) <= 0:
                        break
                    result = send_all(sock, data)
                    if result < len(data):
                        raise Exception('failed to send all data')
        finally:
            sock.close()
            remote.close()

    def encrypt(self, data):
        return data

    def decrypt(self, data):
        return data

    def send_encrypt(self, sock, data):
        sock.send(data)

    def handle(self):
        try:
            print 'from ', self.client_address
            sock = self.connection
            sock.recv(262)
            sock.send("\x05\x00")
            data = self.rfile.read(4) or '\x00' * 4
            print ord(data[0]), 'xxxxxxxx', ord(data[1]), ord(data[2]), ord(data[3])
            mode = ord(data[1])
            if mode != 1:
                logging.warn('mode != 1')
                return
            addrtype = ord(data[3])
            addr_to_send = data[3]
            if addrtype == 1:
                addr_ip = self.rfile.read(4)
                addr = socket.inet_ntoa(addr_ip)
                addr_to_send += addr_ip
            elif addrtype == 3:
                addr_len = self.rfile.read(1)
                print ord(addr_len)
                addr = self.rfile.read(ord(addr_len))
                print addr
                addr_to_send += addr_len + addr
            elif addrtype == 4:
                addr_ip = self.rfile.read(16)
                addr = socket.inet_ntop(socket.AF_INET6, addr_ip)
                addr_to_send += addr_ip
            else:
                logging.warn('addr_type not support')
                # not support
                return
            addr_port = self.rfile.read(2)
            addr_to_send += addr_port
            port = struct.unpack('>H', addr_port)
            try:
                reply = "\x05\x00\x00\x01"
                reply += socket.inet_aton('0.0.0.0') + struct.pack(">H", 22)
                self.wfile.write(reply)
                # reply immediately
                remote = socket.create_connection((SERVER, REMOTE_PORT))
                self.send_encrypt(remote, addr_to_send)
                logging.info('connecting %s:%d' % (addr, port[0]))
            except socket.error, e:
                logging.warn(e)
                return
            self.handle_tcp(sock, remote)
        except socket.error, e:
            logging.warn(e)

if __name__ == '__main__':
    os.chdir(os.path.dirname(sys.argv[0]) or '.')

    SERVER = '127.0.0.1'
    REMOTE_PORT = 1988
    PORT = 1080
    KEY = 'crack'
    METHOD = 'aes-256-cfb'

    logging.basicConfig(
        level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S', filemode='a+')
    try:
        server = ThreadingTCPServer(('', PORT), Socks5Server)
        server.allow_reuse_address = True
        logging.info("starting server at port %d ..." % PORT)
        server.serve_forever()
    except socket.error, e:
        logging.error(e)
