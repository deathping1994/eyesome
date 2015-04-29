#!/bin/env python
"""
**File:** chatserver.py

Chat Server with Threading

Copyright 2009, Tim Bower: Apache Open Source License
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
import sys
import os
import subprocess
import threading
import time
#import traceback
from itertools import cycle

MAX_INDEX = 100                      # The max of cyclic index
MAX_LEN = 10                         # Message queue length
host = ''                            # Bind to all interfaces
port = 50000

def mesg_index(old, last, new):
    """
    :param old: integer index of oldest (first) message in queue
    :param last: integer index of last message read by the client thread
    :param new: integer index of newest (last) message in the queue

    This computes the index value of the message queue from where the reader
    should return messages.  It accounts for having a cyclic counter.
    This code is a little tricky because it has to catch all possible
    combinations.
    """
    if new >= old:
        # normal case
        if last >= old and last < new:
            return (last - old + 1)
        else:
            return 0
    else:
        # cyclic roll over (new < old)
        if last >= old:
            return (last - old + 1)
        elif last < new:
            return (MAX_INDEX - old + last)
        else:
            return 0

class MSGQueue(object):
    """
    Manage a queue of messages for Chat, the threads will read and write to
    this object.  This is an implementation of the readers - writers problem
    with a bounded buffer.
    """
    def __init__(self):
        self.msg = []
        self.cyclic_count = cycle(range(MAX_INDEX))
        self.current = -1
        self.readers = 0
        self.writers = 0
        self.mutex1 = threading.Lock()
        self.mutex2 = threading.Lock()
        self.readPending = threading.Lock()
        self.writeBlock = threading.Lock()
        self.readBlock = threading.Lock()

# This is kind of complicated locking stuff. Don't worry about why there
# are so many locks, it just came from a book showing the known solution to
# the readers and writers problem. You may wonder if so many locks and
# semaphores are really needed.  Well, lots of of really smart people have
# studied the readers and writers problem and this is what they came up
# with as a solution that works with no deadlocks.  The safe plan for us is
# to just use a known solution.

# The only code I did not take directly from a book is what's inside the
# critical section for the reader and writer. The messages are kept in a
# list.  Each list is a tuple containing an index number, a time stamp and
# the message.  Each thread calls the reader on a regular basis to check if
# there are new messages that it has not yet sent to it's client.
# To keep the list from growing without bound, if it is at the MAX_LEN size,
# the oldest item is removed when a new item is added.

# The basic idea of the readers and writers algorithm is to use locks to
# quickly see how many other readers and writers there are.  writeBlock is the
# only lock held while reading the data.  Thus the reader only prevents writers
# from entering the critical section.  Both writeBlock and readBlock are held
# while writing to the data.  Thus the writer blocks readers and other writers.
# So, multiple readers or only one writer are allowed to access the data at a
# given time.  Multiple readers are allowed because the reader does not modify
# the data.  But since the writer does change the data, we can only allow one
# writer access to the critical section at a time.  We also don't want a reader
# in the critical section while a writer is there because the writer could mess
# up the reader by changing the data in the middle of it being read.


    def reader(self, lastread):
        "Reader of readers and writers algorithm"
        self.readPending.acquire()
        self.readBlock.acquire()
        self.mutex1.acquire()
        self.readers = self.readers + 1
        if self.readers == 1: self.writeBlock.acquire()
        self.mutex1.release()
        self.readBlock.release()
        self.readPending.release()
        # here is the critical section
        if lastread == self.current: # or not len(self.msg):
            retVal = None
        else:
            MsgIndex = mesg_index(self.msg[0][0], lastread, self.current)
            retVal = self.msg[MsgIndex:]
        # End of critical section
        self.mutex1.acquire()
        self.readers = self.readers - 1
        if self.readers == 0: self.writeBlock.release()
        self.mutex1.release()
        return retVal

    def writer(self, data):
        "Writer of readers and writers algorithm"
        self.mutex2.acquire()
        self.writers = self.writers + 1
        if self.writers == 1: self.readBlock.acquire()
        self.mutex2.release()
        self.writeBlock.acquire()
        # here is the critical section
        self.current = self.cyclic_count.next()
        self.msg.append((self.current, time.localtime(), data))
        while len(self.msg) > MAX_LEN:
            del self.msg[0]     # remove oldest item
        # End of critical section
        self.writeBlock.release()
        self.mutex2.acquire()
        self.writers = self.writers - 1
        if self.writers == 0: self.readBlock.release()
        self.mutex2.release()

def sendAll(sock, lastread):
    "Get any unread messages and send them to the client"
    global chatQueue
    reading = chatQueue.reader(lastread)
    if reading == None: return lastread
    for (last, timeStmp, msg) in reading:
        sock.send("At %s -- %s" % (time.asctime(timeStmp), msg))
        
    return last

def clientExit(sock, peer, error=None):
    "Report that a client has exited the chat session."
    # this function just cuts down on some code duplication
    global chatQueue
    print "A disconnect by " + peer
    if error:
        msg = peer + " has exited -- " + error + "\r\n"
    else:
        msg = peer + " has exited\r\n"
    chatQueue.writer(msg)

def handlechild(clientsock):
    """
    The function that is ran as the thread to handle a client connection.
    It does the sending and receiving of data for one client
    """
    global chatQueue
    # lastreads of -1 gets all available messages on first read, even 
    # if message index cycled back to zero.
    lastread = -1
    # the identity of each user is called peer - they are the peer on the other
    # end of the socket connection. 
    peer = clientsock.getpeername()
    print "Got connection from ", peer
    msg = str(peer) + " has joined\r\n"
    chatQueue.writer(msg)
    while 1:
        # check for and send any new messages
        lastread = sendAll(clientsock, lastread)
        try:
            data = clientsock.recv(4096)
        except socket.timeout:
            continue
        except socket.error:
            # caused by main thread doing a socket.close on this socket
            # It is a race condition if this exception is raised or not.
            print "Server shutdown"
            return
        except:  # some error or connection reset by peer
            clientExit(clientsock, str(peer))
            break
        if not len(data): # a disconnect (socket.close() by client)
            clientExit(clientsock, str(peer))
            break

        # Process the message received from the client
        # First check if it is a one of the special chat protocol messages.
        if data.startswith('/nick'):
            oldpeer = peer
            peer = data.replace('/nick', '', 1).strip()
            if len(peer):
                chatQueue.writer("%s now goes by %s\r\n" \
                                % (str(oldpeer), str(peer)))
            else: peer = oldpeer

        elif data.startswith('/quit'):
            bye = data.replace('/quit', '', 1).strip()
            if len(bye):
                msg = "%s is leaving now -- %s\r\n" % (str(peer), bye)
            else:
                msg = "%s is leaving now\r\n" % (str(peer))
            chatQueue.writer(msg)
            break            # exit the loop to disconnect
        # elif data.startswith('/execute'):
        #     data = data.replace('/execute', '', 1).strip()
        #     chatQueue.writer(data)
        else:
            # Not a special command, but a chat message
            chatQueue.writer("Message from %s:\r\n\t%s\r\n" \
                                % (str(peer), data))

    #-- End looping for messages from/to the client
    # Close the connection
    clientsock.close()

# Begin the main part of the program
def main():
    """
    The parent thread that listens for connections and spawns a child thread
    to handle each connection.
    """
    global chatQueue
    clients = []

    # Set up the socket.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(3)

    while 1:
        print "Waiting for Connections"
        try:
            clientsock, clientaddr = s.accept()
            # set a timeout so it won't block forever on socket.recv().
            # Clients that are not doing anything check for new messages 
            # after each timeout.
            clientsock.settimeout(1)
        except KeyboardInterrupt:
            # shutdown - force the threads to close by closing their socket
            s.close()
            for sock in clients:
                sock.close()
            break
        #except:
        #    traceback.print_exc()
        #    continue

        clients.append(clientsock)
        t = threading.Thread(target = handlechild, args = [clientsock])
        t.setDaemon(1)
        t.start()

if __name__ == '__main__':
    # One global message queue, which uses the readers and writers
    # synchronization algorithm.
    chatQueue = MSGQueue()
    main()
