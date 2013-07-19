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

from gi.repository import Gtk


class PlayerWindow(object):
    """This is a very simple gtk window for the players to draw on.
    It supports fullscreen."""
    def __init__(self):
        window = Gtk.Window()
        window.set_title("SYNEPlayer")
        window.set_default_size(600, -1)
        window.connect("destroy", Gtk.main_quit, "WM destroy")
        self.movie_window = Gtk.DrawingArea()
        window.add(self.movie_window)
        self.fullscreen = True
        window.fullscreen()
        window.connect("key_press_event", self.key_press_handler)
        window.show_all()

    def key_press_handler(self, widget, event):
        if event.keyval == 102:
            if self.fullscreen:
                widget.unfullscreen()
                self.fullscreen = False
            else:
                widget.fullscreen()
                self.fullscreen = True
