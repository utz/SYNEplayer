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

import sys

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, Gtk, GObject

GObject.threads_init()
Gst.init(None)

from .playerwindow import PlayerWindow

from gi.repository import GdkX11, GstVideo


class Player(object):
    """
        This is a simple pipeline for a video player based on
        decodebin/autovideosink. This pipeline will loop the video file.
    """
    def __init__(self, filepath, window=None):
        if window is None:
            self.window = PlayerWindow()
        else:
            self.window = window

        #build the pipeline
        self.pipeline = self.get_pipeline(filepath)
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.on_message)
        self.bus.enable_sync_message_emission()
        self.bus.connect("sync-message::element",
           self.on_sync_message)

        self.pipeline.set_state(Gst.State.PAUSED)
        #after setting to STATE_PAUSED the player is prerolling
        self.prerolling = True

    def key_press_handler(self, widget, event):
        """F key handler for fullscreen"""
        if event.keyval == 102:
            if self.fullscreen:
                widget.unfullscreen()
                self.fullscreen = False
            else:
                widget.fullscreen()
                self.fullscreen = True

    def get_pipeline(self, filepath):
        """A basic decodebin/autovideosink pipeline with no audio support"""
        return Gst.parse_launch('filesrc location={0} ! '.format(filepath)\
            + 'decodebin ! autovideosink')

    def on_sync_message(self, bus, message):
        """Whe handle sync messages to put the video in a GTK DrawingArea"""
        if message.get_structure().get_name() == 'prepare-window-handle':
            message.src.set_window_handle(self.window.movie_window
                .get_property('window').get_xid())

    def on_message(self, bus, message):
        """Messages Handler"""
        t = message.type
        if t == Gst.MessageType.SEGMENT_DONE:
            #When segment is done, we seek the video to t=0
            self.pipeline.seek_simple(Gst.FORMAT_TIME, Gst.SEEK_FLAG_SEGMENT, 0)
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)
        elif t == Gst.MessageType.ASYNC_DONE:
            if self.prerolling:
                """
                    When the MESSAGE_ASYNC_DONE is emitted first time,
                    prerolling is done. Then we seek to t=0 to enable
                    SEGMENT_DONE message emission.
                """
                self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH
                    | Gst.SeekFlags.SEGMENT, 0)
                self.pipeline.set_state(Gst.State.PLAYING)
                #prerolling is done!
                self.prerolling = False

    def stop(self):
        """Stop the player"""
        self.pipeline.set_state(Gst.State.NULL)


class MasterPlayer(Player):
    """
        This class extends the basic Player creating a gst.NetTimeProvider to be
        used by the slaves. Code here is taken from Andy Wingo examples.
    """
    def __init__(self, filepath, port, window=None):
        super(MasterPlayer, self).__init__(filepath, window)

        self.clock = self.pipeline.get_clock()
        self.pipeline.use_clock(self.clock)
        self.clock_provider = Gst.NetTimeProvider(self.clock, None, port)
        self.base_time = self.clock.get_time()
        self.pipeline.set_new_stream_time(Gst.CLOCK_TIME_NONE)
        self.pipeline.set_base_time(self.base_time)

    def get_base_time(self):
        return self.base_time


class SlavePlayer(Player):
    """
        This class extends the basic player creating making it use a gst.NetClientClock
        and setting a base_time taken from the Master. This creates a SlavePlayer that
        is synchronized with the MasterPlayer.
    """
    def __init__(self, filepath, ip, port, base_time, window=None):
        super(SlavePlayer, self).__init__(filepath, window)
        self.ip = ip
        self.port = port
        self.set_clock(base_time)

    def get_base_time(self):
        return self.pipeline.get_base_time()

    def set_clock(self, base_time):
        #Code here is taken from Andy Wingo examples.
        self.pipeline.set_new_stream_time(Gst.CLOCK_TIME_NONE)
        self.base_time = base_time
        self.clock = Gst.NetClientClock(None, self.ip, self.port, base_time)
        self.pipeline.set_base_time(base_time)
        self.pipeline.use_clock(self.clock)

if __name__ == '__main__':
    """
        This is a simple main meant to test the behaviour of SlavePlayer and MasterPlayer
    """
    if sys.argv[1] == 'test':
        master = MasterPlayer('/home/phas/Downloads/A.ogg', 20000)
        slave = SlavePlayer('127.0.0.1', 20000, master.base_time)
        slave.pipeline.base_time = master.base_time
    elif sys.argv[1] == 'master':
        player = MasterPlayer(20000)
        print("base_time={0}".format(player.base_time))
    elif sys.argv[1] == 'slave':
        slave = SlavePlayer(sys.argv[2], 20000, int(sys.argv[3]))
        slave.pipeline.base_time = int(sys.argv[3])
    elif sys.argv[1] == 'base':
        player = Player('/home/phas/Downloads/A.ogg')

    #Gtk.gdk.threads_init()
    Gtk.main()
