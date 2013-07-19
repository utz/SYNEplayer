#!/usr/bin/env python
"""
Copyright (C) 2011 by Riccardo Cagnasso, Paolo Podesta'

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

"""
    SYnchronized NEtwork Player is a simple application that let you start some
    video players, a master and some slaves, synchronized over a network using
    gst.NetTimeProvider / gst.NetClientClock. The synchronization code is taken
    from some examples by Andy Wingo (thanks Andy!). The videos will continue to
    play in loop.

    The player is a basic decodebin / autovideosink based pipeline, no audio support
    is provided but it's easy to add it.

    SYNEPlayer is designed to survive the death of one of his component, even if the
    master dies, the clients are meant to re-synchronize when it comes up again.
"""

import threading
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import xmlrpclib
import time
import argparse

from syneplayer import *


class MasterServer(object):
    """This object contains method that will be made available from SimpleXMLRPCServer"""
    def __init__(self, master_player):
        self.master_player = master_player

    def get_base_time(self):
        """Gets the base time of the master server"""
        return str(self.master_player.get_base_time())


class requestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)


class MasterServerThread(threading.Thread):
    """This object is the thread of SimpleXMLRPCServer for the master"""
    def __init__(self, master_server, ip, rpcport):
        super(MasterServerThread, self).__init__()
        self.master_server = master_server
        self.rpcport = rpcport
        self.ip = ip

    def run(self):
        """Here we create the XMLRPCServer and put it to listen for requests"""
        self.server = SimpleXMLRPCServer(('', self.rpcport),
            requestHandler=requestHandler, allow_none=True)

        self.server.register_introspection_functions()
        self.server.register_instance(self.master_server)
        self.server.serve_forever()


class SlaveControllerThread(threading.Thread):
    """
        This thread is in control of a SlavePlayer.
        It waits for the base_time from the master and then it starts the server,
        then it continues polling the master for changes in the base_time (e.g. if
        the master reboot) in that case it kills the current player and starts a new
        one (there should be a better way to do this...)
    """
    def __init__(self, filepath, ip, port, rpcport):
        super(SlaveControllerThread, self).__init__()
        self.filepath = filepath
        self.ip = ip
        self.port = port
        self.rpcport = rpcport

        self.master_server = None
        self.slave = None
        self.running = True

    def run(self):
        while self.running:
            while self.master_server is None:
                try:
                    self.master_server = xmlrpclib.ServerProxy('http://{0}:{1}'
                        .format(self.ip, self.rpcport))
                except Exception:
                    print("Master not ready")
                    time.sleep(5)

            try:
                base_time = long(self.master_server.get_base_time())
            except Exception:
                print("Master not responding")
            else:
                if self.slave is None:
                    self.slave = SlavePlayer(self.filepath, self.ip,
                        self.port, base_time)
                elif base_time != self.slave.get_base_time():
                    print("Base time changed, restarting slave")
                    self.slave.stop()
                    self.slave = SlavePlayer(self.filepath, self.ip, self.port,
                        base_time, self.slave.window)

                time.sleep(10)

    def stop_player(self):
        self.slave.stop()
        self.running = False


def master_main(filepath, ip, port, rpcport):
    """Launches a master"""
    player = MasterPlayer(filepath, port)
    ms = MasterServer(player)
    mst = MasterServerThread(ms, ip, rpcport)
    mst.start()

    gtk.gdk.threads_init()
    gtk.main()

    mst.server.shutdown()
    player.stop()


def slave_main(filepath, ip, port, rpcport):
    """Launches a slave"""
    sct = SlaveControllerThread(filepath, ip, port, rpcport)
    sct.start()

    gtk.gdk.threads_init()
    gtk.main()

    sct.stop_player()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='syneplayer',
        description='Start a syneplayer master or server')
    parser.add_argument('-c', '--clock-port', type=int, default=20000,
        help='Specify the port for the netclock')
    parser.add_argument('-r', '--rpc-port', type=int, default=8000,
        help='Specify the port for the xmlrpcserver')                       
    parser.add_argument('-i', '--master-ip', type=str, default='127.0.0.1',
        help='Specify the ip of the master server for the slave to connect')
    parser.add_argument('-f', '--file', type=str, required=True,
        help='Specify the full path of the file to be played')
    parser.add_argument('type', choices=['master', 'slave'],
        help="Specify if launch the master or the slave")

    args = parser.parse_args()

    if args.type == 'master':
        master_main(args.file, args.master_ip, args.clock_port, args.rpc_port)
    elif args.type == 'slave':
        slave_main(args.file, args.master_ip, args.clock_port, args.rpc_port)
