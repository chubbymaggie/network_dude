#!/usr/bin/python

"""
Copyright (C) 2015 - Brian Caswell <bmc@lungetech.com>
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import argparse
import logging
import select
import socket
import struct
import time
import sys


class Connection(object):
    CLIENT, SERVER = (0, 1)
    HEADER_LEN = 15

    def __init__(self, port, filename):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.sock.bind(('', port))

        self.pcap_handle = self.open_pcap(filename)

        logging.info('logging network appliance traffic from port %d', port)

    def __call__(self):
        while True:
            data = self.sock.recvfrom(0xFFFF)[0]
            packet = self.parse(data)
            if packet is None:
                continue

            csid, connection_id, msg_id, side, message = packet

            logging.info('csid: %d connection: %d message_id: %d side: %s '
                          'message: %s', csid, connection_id, msg_id, side,
                          message.encode('hex'))

            self.write_packet(data)

    def open_pcap(self, filename):
        if filename is None:
            return None

        PCAP_MAGIC = 0xa1b2c3d4L
        LINK_TYPE = 1  # ethernet

        PCAP_VERSION_MAJOR = 2
        PCAP_VERSION_MINOR = 4
        if filename is None:
            return None

        pcap_handle = open(filename, 'w')
        header = struct.pack('>IHHIIII', PCAP_MAGIC, PCAP_VERSION_MAJOR,
                             PCAP_VERSION_MINOR, 0, 0, 1500, LINK_TYPE)

        pcap_handle.write(header)
        return pcap_handle

    def write_packet(self, data):
        if self.pcap_handle is None:
            return

        timestamp = time.time()
        tv_sec = int(timestamp)
        tv_usec = int((float(timestamp) - int(timestamp)) * 1000000.0)

        packet = '\x00\x00\x00\x00\x00\x00' + '\x00\x00\x00\x00\x00\x00' + '\xff\xff' + data

        packet_len = len(packet)
        packet_header = struct.pack('>IIII', tv_sec, tv_usec, packet_len, packet_len)

        self.pcap_handle.write(packet_header)
        self.pcap_handle.write(packet)
        self.pcap_handle.flush()

    def parse(self, data):
        if len(data) < Connection.HEADER_LEN:
            logging.error('invalid message length: %d', len(data))
            return None

        header = data[:Connection.HEADER_LEN]
        message = data[Connection.HEADER_LEN:]
        csid, connection_id, msg_id, msg_len, side = struct.unpack('<LLLHB', header)
        if len(message) != msg_len:
            logging.error('invalid message.  actual: %d expected: %d', len(data), msg_len)
            return None

        if side == Connection.CLIENT:
            side = 'client'
        else:
            side = 'server'

        return (csid, connection_id, msg_id, side, message)

    def log(self, data):
        if self.pcap_file is None:
            return

        pass


def main():
    """ Parse arguments and setup the server """

    log_level = logging.INFO

    logging.basicConfig(format='%(asctime)s - %(levelname)s : %(message)s',
                        level=log_level, stream=sys.stdout)

    log = Connection(1999, "captured_cb_log.pcap")
    log()

if __name__ == '__main__':
    main()