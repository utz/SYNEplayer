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

import threading
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import xmlrpclib
import sys
import time
import argparse

from syneplayer import *

class MasterServer(object):
    def __init__(self, master_player):
        self.master_player=master_player
        
    def get_base_time(self):
        return str(self.master_player.get_base_time())

class requestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths=('/RPC2',)
       
class MasterServerThread(threading.Thread):
    def __init__(self, master_server, ip, rpcport):
        super(MasterServerThread, self).__init__()
        self.master_server=master_server
        self.rpcport=rpcport
        self.ip=ip
        
        
    def run(self):
        self.server=SimpleXMLRPCServer(('', self.rpcport),
            requestHandler=requestHandler, allow_none=True)
            
        self.server.register_introspection_functions()
        self.server.register_instance(self.master_server)
        self.server.serve_forever()

class SlaveControllerThread(threading.Thread):
    def __init__(self, filepath, ip, port, rpcport):
        super(SlaveControllerThread, self).__init__()
        self.filepath=filepath
        self.ip=ip
        self.port=port
        self.rpcport=rpcport
        
        self.master_server=None
        self.slave=None
        
    def run(self):
        while True:
            while self.master_server is None:
                try:
                    self.master_server=xmlrpclib.ServerProxy('http://{0}:{1}'.format(self.ip, self.rpcport))
                except Exception:
                    print "Master not ready"
                time.sleep(1)
        
            try:
                base_time=long(self.master_server.get_base_time())
            except Exception:
                print "Master not responding"
            else:
                if self.slave is None:
                    self.slave=SlavePlayer(self.filepath, self.ip, self.port, base_time)
                elif base_time!=self.slave.get_base_time():
                    self.slave.stop()
                    self.slave=SlavePlayer(self.filepath, self.ip, self.port, base_time, self.slave.window)
                    
            time.sleep(2)
    
    def stop_player(self):
        self.slave.stop()

def master_main(filepath, ip, port, rpcport):
    player=MasterPlayer(filepath, port)
    ms=MasterServer(player)
    mst=MasterServerThread(ms, ip, rpcport)
    mst.start()
    
    gtk.gdk.threads_init()
    gtk.main()
    
    mst.server.shutdown()
    player.stop()

def slave_main(filepath, ip, port, rpcport):
    sct=SlaveControllerThread(filepath, ip, port, rpcport)
    sct.start()
    
    gtk.gdk.threads_init()
    gtk.main()
    
    sct.stop_player()
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='syneplayer', description='Start a syneplayer master or server')
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

    
    if args.type=='master':
        master_main(args.file, args.master_ip, args.clock_port, args.rpc_port)
    elif args.type=='slave':
        slave_main(args.file, args.master_ip, args.clock_port, args.rpc_port)
        
