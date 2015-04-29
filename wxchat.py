#!/bin/env python

"""
**File:** wxchat.py

The client application (with GUI) to go along with the chat server.
wxchat Requires wxPython.

Copyright 2009, Tim Bower: Apache Open Source License
"""

# History:
# Summer 2008 - just used putty (in Windows) for the client application.
# Focus was on the development of the server.
#
# April 2009 - Developed first graphical client using a modified graphics
#   module from book "Introduction to Programming using Python"
#   by John Zelle, which uses the TK widgets.
#
# June 2009 - For much nicer graphics, ported client to wxPython.

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

import string
import threading
import wx
import os
import sys

from chatnetworking import ChatConnect, defaulthost
import rendezvous
# import pdb

xmax = 500
ymax = 500
MAIN_WINDOW_DEFAULT_SIZE = (xmax,ymax)

class ChatFrame(wx.Frame):
    """
    The main class containing the wxPython graphical interface.
    """
    def __init__(self, parent, id, title):
        style=wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, parent, id, title=title,
                          size=MAIN_WINDOW_DEFAULT_SIZE, style=style)
        self.Center() # open in the centre of the screen
        wx.BeginBusyCursor()
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour('cadet blue')
        self.host = host  # host is global
        self.Bind(wx.EVT_CLOSE, self.OnExit)
        #create a StatusBar and give it 2 columns
        self.statusBar = self.CreateStatusBar()
        self.statusBar.SetFieldsCount(2)
        # A menu to set the server's host name...
        self._createMenuBar()
        banner = wx.StaticText(self.panel, -1,
                    "Eye-Some\n"
                    "Collaboration Tool",
                    #size = (xmax, -1), pos = (xmax/2,2),
                    style = wx.ALIGN_CENTER)
        banner.SetFont(wx.Font(16, wx.ROMAN, wx.SLANT, wx.NORMAL))
        # The window for reading chat messages
        self.readWin = wx.TextCtrl(self.panel, -1,
             #size = (xmax*.95, ymax*0.1),
             style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        self.readWin.SetBackgroundColour('wheat')
        # The windows for writing chat messages
        self.writeWin = wx.TextCtrl(self.panel, -1,
             size = (xmax*.95, ymax*0.15),
             style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        self.writeWin.SetBackgroundColour('light blue')
        self.inputWin = wx.TextCtrl(self.panel, -1,
             size = (xmax*.95, ymax*0.1),
             style = wx.TE_MULTILINE | wx.TE_PROCESS_ENTER | wx.TE_WORDWRAP)
        self.inputWin.SetBackgroundColour('light blue')
        self.Bind(wx.EVT_TEXT_ENTER, self.send)

        # A row of buttons, which is a horizontal BoxSizer
        buttonRow = self._makeButtons()
        # Create a BoxSizer which grows in the vertical direction
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(banner, 0,
                wx.ALIGN_TOP | wx.ALL | wx.FIXED_MINSIZE | wx.ALIGN_CENTER_HORIZONTAL, 5)
        sizer.Add(self.readWin, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.writeWin, 0,
                wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT | wx.ALIGN_BOTTOM, 5)
        sizer.Add(self.inputWin, 0,
                wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT | wx.ALIGN_TOP, 5)
        sizer.Add(buttonRow, 0,
                wx.ALIGN_BOTTOM | wx.ALL | wx.FIXED_MINSIZE, 5)
        # Tell our panel to use this new Sizer
        self.panel.SetSizer(sizer)
        # Tell our panel to calculate the size of its items.
        self.panel.Layout()

        #-- Graphics now set-up, set-up Chat client
        self.rendezvous = rendezvous.Rendezvous(
                                    self.connected,
                                    self.chatDisplay,
                                    self.lostConnection)
        self.readPos = []
        self.writePos = []
        self.here = True
        self.blank_line_len = len(os.linesep)
        self._not_connected()
        wx.EndBusyCursor()
    #-- end of __init__

    def _createMenuBar(self):
        "Create a menu bar for setting the server host name, and Exit items"
        menuServ = wx.Menu()
        ResetMenuItem = menuServ.Append(-1, '&Reset Server Name',
                'Reset the server to the default name')
        HostMenuItem = menuServ.Append(-1, '&Set Server Name',
                "Set the server's host name")
        menuServ.AppendSeparator()
        ExitMenuItem = menuServ.Append(-1, '&Exit',
                'Exit the chat application')

        self.Bind(wx.EVT_MENU, self.resetServer, ResetMenuItem)
        self.Bind(wx.EVT_MENU, self.setServer, HostMenuItem)
        self.Bind(wx.EVT_MENU, self.quit, ExitMenuItem)

        menuBar = wx.MenuBar()
        menuBar.Append(menuServ, '&Server')
        self.SetMenuBar(menuBar)

    def _makeButtons(self):
        "A horizontal sizer (row) of buttons"
        quitBtn = wx.Button(self.panel, -1, 'Quit')
        self.connectBtn = wx.Button(self.panel, -1, 'Connect')
        self.nick_nameBtn = wx.Button(self.panel, -1, 'Set Nick Name')
        
        self.sendBtn = wx.Button(self.panel, -1, 'send')

        quitBtn.SetToolTip(wx.ToolTip('Exit the chat application'))
        self.connectBtn.SetToolTip(wx.ToolTip('Connect to the chat server'))
        self.nick_nameBtn.SetToolTip(wx.ToolTip('Set name you go by'))
        self.Bind(wx.EVT_BUTTON, self.quit, quitBtn)
        self.Bind(wx.EVT_BUTTON, self.connect, self.connectBtn)
        self.Bind(wx.EVT_BUTTON, self.nickName, self.nick_nameBtn)
        self.Bind(wx.EVT_BUTTON, self.send, self.sendBtn)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add( quitBtn, 0, wx.LEFT, 5)
        row.Add( self.connectBtn, 0, wx.LEFT, 5)
        row.Add( self.nick_nameBtn, 0, wx.LEFT, 5)
        row.Add( self.sendBtn, 0, wx.LEFT | wx.RIGHT, 5)
        return row

    def resetServer(self, event):
        "Menu item call back"
        self.host = defaulthost
        dlg = wx.MessageDialog(self,
                "The server is now set to %s" % self.host,
                "Server Reset to Default", style=wx.OK )
        dlg.ShowModal()
        dlg.Destroy()
        self.add_readWin("\nServer is now set to %s.\n" % self.host)

    def setServer(self, event):
        "Menu item call back"
        dlg = wx.TextEntryDialog(self,
                "Enter the server's host name or IP address",
                "New Eyesome Server", style=wx.OK | wx.CANCEL )
        if dlg.ShowModal() == wx.ID_OK:
            self.host = dlg.GetValue()
        dlg.Destroy()
        self.add_readWin("\nThe Eyesome server is now set to %s.\n" % self.host)


    def _not_connected(self):
        "The state of client is not connected - set the GUI to match."
        self.connected = False
        self.statusBar.SetStatusText('Not connected to Eyesome Server', 1)
        self.statusBar.SetStatusText(
                "The 'Connect' button lets you connect to Eyesome Server", 0)
        self.nick_nameBtn.Disable()
        self.nick_nameBtn.Hide()
        self.sendBtn.Disable()
        self.sendBtn.Hide()
        self.connectBtn.SetDefault()
        self.clear_readWin()
        self.add_readWin(
            "This window shows output of your command.")
        self.clear_writeWin()
        self.add_writeWin(
            "This is the window for writing commands.")

    # Next several functions implement auto-scrolling in the read and write
    # windows.
    def clear_readWin(self):
        "Clear the reading widow"
        self.readWin.Clear()
        self.readPos = []

    def add_readWin(self, msg):
        "Add text to the reading window"
        self.readWin.AppendText(msg)
        self.readPos.append(self.readWin.GetInsertionPoint())
        if len(self.readPos) > 10:
            clear = self.readPos.pop(0)
            self.readWin.Remove(0, clear)
            for i in range(len(self.readPos)):
                self.readPos[i] -= clear
        if self.readWin.GetNumberOfLines() > 15:
            self.readWin.ScrollLines(10)

    def clear_writeWin(self):
        "Clear the writing window"
        self.writeWin.Clear()
        self.writePos = []

    def add_writeWin(self, msg):
        "Add text to the writing window"
        if len(msg):
            self.writeWin.AppendText(msg)
            self.writePos.append(self.writeWin.GetInsertionPoint())
        while len(self.writePos) > 10 or \
              (len(self.writePos) and self.writePos[0] <= self.blank_line_len):
            clear = self.writePos.pop(0)
            self.writeWin.Remove(0, clear)
            for i in range(len(self.writePos)):
                self.writePos[i] -= clear
        if self.writeWin.GetNumberOfLines() > 5:
            self.writeWin.ScrollLines(5)

    def getText(self):
        "Read text in from user"
        message = string.strip(self.inputWin.GetValue())
        self.inputWin.Clear()
        self.inputWin.SetInsertionPoint(0)
        if len(message):
            self.add_writeWin(message + '\n')
            return message
        else:
            return ''

    def connect(self, event):
        """
        Button call back, may be either *Connect* or *Disconnect* (same button)
        """
        wx.BeginBusyCursor()
        if self.connected:
            # a disconnect request
            name = self.getText()
            self.net.send("/quit " + name)
            self.add_writeWin('\n')
            self.net.join()
            # Note: finish this up in lostConnection
        else:
            # a connect request
            self.add_readWin('\n')
            # A thread to listen to the network and 
            # display messages from server
            self.net = ChatConnect(self.host,
                            self.rendezvous.connected,
                            self.rendezvous.display,
                            self.rendezvous.lost,
                            )
            self.net.start()
            # Note: finish this up in connected
        #--
        wx.EndBusyCursor()

    def send(self, event):
        "*Send* button (and return key) event call back"
        if self.connected:
            sendData = self.getText()
            if len(sendData):
                self.net.send(sendData)
            else:
                self.add_writeWin('\n')
        self.inputWin.SetFocus()

    def nickName(self, event):
        "*Set Nick Name* button call back"
        if self.connected:
            name = self.getText()
            if len(name):
                self.net.send( "/nick " + name )
                self.statusBar.SetStatusText("Your Nick Name is " + name, 0)
            else:
                self.add_writeWin('Enter a name to set your Nick Name\n')
        self.inputWin.SetFocus()

    # def brb(self, event):
    #     "*Be Right Back* and *I'm Back* button call back"
    #     msg = self.getText()
    #     if self.here:
    #         # switch from here to away
    #         self.here = False
    #         self.brbBtn.SetLabel("I'm Back")
    #         self.net.send("/brb " + msg)
    #         self.statusBar.PushStatusText("Click 'I'm Back' to resume chat", 0)
    #         self.statusBar.PushStatusText("Your status is away", 1)
    #         self.nick_nameBtn.Disable()
    #         self.nick_nameBtn.Hide()
    #         self.sendBtn.Disable()
    #         self.sendBtn.Hide()
    #     else:
    #         # switch from away to here
    #         self.here = True
    #         self.brbBtn.SetLabel("Be Right Back")
    #         self.net.send("/back " + msg)
    #         self.statusBar.PopStatusText(0)
    #         self.statusBar.PopStatusText(1)
    #         self.nick_nameBtn.Enable()
    #         self.nick_nameBtn.Show()
    #         self.sendBtn.Enable()
    #         self.sendBtn.Show()
    #     #--
    #     self.inputWin.SetFocus()

    def connected(self):
        """
        Now connected to the Chat server
        Invoked via :func:`wx.CallAfter` in :mod:`rendezvous`.
        """
        self.connected = True
        self.connectBtn.SetLabel('Disconnect')
        self.nick_nameBtn.Enable()
        self.nick_nameBtn.Show()
        
        self.sendBtn.Enable()
        self.sendBtn.Show()
        self.sendBtn.SetDefault()
        self.statusBar.SetStatusText(
            'Connected to a Eye-Some server', 1)
        self.statusBar.SetStatusText(
            "return or 'send' to send message", 0)
        self.add_readWin('\n\nConnected to Eyesome server\n\n')
        self.clear_writeWin()
        self.add_writeWin(
            "Enter a name click on 'Set Nick Name' to set your identity.\n"
            "Type a message and press return or 'Send'.\n")
        self.inputWin.SetFocus()

    def chatDisplay(self, msg):
        """
        Message to display from the chat server.
        Invoked via :func:`wx.CallAfter` in :mod:`rendezvous`.
        """
        self.add_readWin(msg)

    def lostConnection(self, msg):
        """"
        We lost our connection to the chat server
        Invoked via :func:`wx.CallAfter` in :mod:`rendezvous`.
        """
        self.connectBtn.SetLabel('Connect')
        self._not_connected()
        self.add_readWin('\n\n'+ msg)
        self.net.join()

    def quit(self, event):
        "*Quit* button call back"
        if self.connected:
            self.connected = False
            self.net.send("/quit" + self.getText())
            self.net.join()
        self.Close(True)

    def OnExit(self, event):
        "Close the application by Destroying the object"
        if self.connected:
            self.net.send("/quit")
            self.net.join()
        self.Destroy()

class App(wx.App):

    def OnInit(self):
        self.frame = ChatFrame(parent=None, id=-1,
                title='Eyesome - Multiparty collaboration tool')
        self.frame.Show()
        self.SetTopWindow(self.frame)
        return True

if __name__ == "__main__":
    # set host name from command line arguments
    # may also be set from menu selection
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = defaulthost
    # make an App object, set stdout to the console so we can see errors
    #app = App()
    app = App(redirect=False)
    app.MainLoop()
