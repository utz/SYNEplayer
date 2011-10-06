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

#!/usr/bin/env python

import threading
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import xmlrpclib
import sys
import time

from syneplayer import *

class MasterServer(object):
    def __init__(self, master_player):
        self.master_player=master_player
        
    def get_base_time(self):
        return str(self.master_player.get_base_time())

class requestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths=('/RPC2',)
       
class MasterServerThread(threading.Thread):
    def __init__(self, master_server):
        super(MasterServerThread, self).__init__()
        self.master_server=master_server
        
        
    def run(self):
        server=SimpleXMLRPCServer(("localhost", 8000),
            requestHandler=requestHandler, allow_none=True)
            
        server.register_introspection_functions()
        server.register_instance(self.master_server)
        print 'foo'
        server.serve_forever()

class SlaveControllerThread(threading.Thread):
    def __init__(self, ip, port):
        super(SlaveControllerThread, self).__init__()
        self.ip=ip
        self.port=port
        
        self.master_server=None
        self.slave=None
        
    def run(self):
        while True:
            while self.master_server is None:
                try:
                    self.master_server=xmlrpclib.ServerProxy('http://localhost:8000')
                except Exception:
                    print "Master not ready"
                time.sleep(1)
        
            try:
                base_time=long(self.master_server.get_base_time())
            except Exception:
                print "Master not responding"
            else:
                print base_time
                if self.slave is None:
                    self.slave=SlavePlayer(self.ip, self.port, base_time)
                elif base_time!=self.slave.get_base_time():
                    self.slave.stop()
                    self.slave=SlavePlayer(self.ip, self.port, base_time)
                    
            time.sleep(2)
        

def master_main(port):
    player=MasterPlayer(port)
    ms=MasterServer(player)
    mst=MasterServerThread(ms)
    mst.start()
    
    gtk.gdk.threads_init()
    gtk.main()

def slave_main(ip, port):
    sct=SlaveControllerThread(ip, port)
    sct.start()
    
    gtk.gdk.threads_init()
    gtk.main()
    
if __name__ == '__main__':
    if sys.argv[1]=='master':
        master_main(20000)
    elif sys.argv[1]=='slave':
        slave_main('127.0.0.1', 20000)
        
