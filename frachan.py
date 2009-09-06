#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# frachan.py
#
# Copyright 2009 Francesco Frassinelli <fraph24@gmail.com>
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#    
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#     GNU General Public License for more details.
#    
#     You should have received a copy of the GNU General Public License
#     along with this program. If not, see <http://www.gnu.org/licenses/>.

""" This is a KISS (Keep It Simple Stupid) free chat program.
    Depends by: pyqt4, twisted-core
    Usage:      python frachan.py
    If you want to start the server side:
        1. You must put "server" at the end of the command
        2. You must edit HOST and PORT (if you want to), lines no. 30-31
"""

###                              Configuration                               ###
PORT = 8880                                 # This is for both
HOST = "frafra.homelinux.org"               # This is only for the client

###                          Libraries and settings                          ###
import functools, getpass, sys, time        # Built-in default libraries
from PyQt4 import QtGui, QtCore             # PyQt4 (Python QT4 bindings)
from twisted.internet import protocol, task # twisted.internet (twisted-core)
from qtreactor import qt4reactor            # Custom Qt4 Twisted reactor
APP = QtGui.QApplication(sys.argv)
qt4reactor.install()
from twisted.internet import reactor        # Twisted reactor

class ServerProtocol(protocol.Protocol):
    """ Server custom protocol """
    def __init__(self, parent):
        self.users = parent.users
        self.chat = parent.chat
    def send(self, line, mode = "replay"):
        line = line.encode("utf-8")
        if mode == "direct":
            self.transport.write("%s\r\n" % line)
        elif mode == "replay":
            for user in self.users:
                if user is not self:
                    user.transport.write("%s\r\n" % line)
        elif mode == "all":
            for user in self.users:
                user.transport.write("%s\r\n" % line)    
    def dataReceived(self, data):
        data = data.decode("utf-8").rstrip().split(" ", 1)
        action = data[0]
        if action == "!nick":
            nick = data[1].replace(" ", "-")
            nicks = [user.text().__str__() for user in self.users.values()]
            while nick in nicks or nick == self.chat.nick:
                if self.users.has_key(self):
                    if nick == self.users[self].text().__str__():
                        break
                nick = "_%s_" % nick
            if self.users.has_key(self):
                for user in self.users.values():
                    if self.users[self] is user:
                        self.send("!list * %s %s" %
                            (self.users[self].text().__str__(), nick),
                            mode = "all")
                        self.users[self].setText(nick)
                        break
            else:
                user = QtGui.QListWidgetItem(nick)
                self.chat.users_box.addItem(user)
                self.users[self] = user
                self.send("!list + %s" % nick)
            self.send("!nick %s" % nick, mode = "direct")
        elif action == "!list":
            nicks = [user.text().__str__() for user in self.users.values()]
            nicks.append(self.chat.nick)
            self.send("!list = %s" % " ".join(nicks), mode = "direct")
        elif action == "!msg":
            text = time.strftime("<br>(%H:%M:%S) ") + data[1]
            self.chat.text_box.moveCursor(QtGui.QTextCursor.End)
            self.chat.text_box.insertHtml(text)
            self.chat.text_box.moveCursor(QtGui.QTextCursor.End)
            self.chat.text_box.ensureCursorVisible()
            self.send(" ".join(data))
    def connectionLost(self, reason):
        if self.users.has_key(self):
            user = self.users[self]
            line = self.chat.users_box.row(user)
            self.chat.users_box.takeItem(line)
            self.send("!list - " + user.text().__str__())
            del self.users[self]

class ServerFactory(protocol.ServerFactory):
    """ Server factory """
    def __init__(self, chat):
        self.chat = chat
        self.users = {}
        self.user = QtGui.QListWidgetItem(self.chat.nick)
        self.chat.users_box.addItem(self.user)
        task.LoopingCall(self.ping).start(10*60)
    def ping(self):        for user in self.users:
            user.send("!ping")
    def buildProtocol(self, addr):
        return ServerProtocol(self)
    def send(self, line):
        for user in self.users:
            user.transport.write(line + "\r\n")
    def nick(self):
        nick = self.chat.nick_box.text().toUtf8().__str__().replace(" ", "-")
        nicks = [user.text().__str__() for user in self.users.values()]
        while nick in nicks:
            nick = "_%s_" % nick
        self.send("!list * %s %s" % (self.chat.nick, nick))
        self.user.setText(nick)
        self.chat.nick = nick
        self.chat.nick_box.setText(nick)

class ClientProtocol(protocol.Protocol):
    """ Client custom protocol """
    def __init__(self, parent):
        self.users = parent.users
        self.chat = parent.chat
        self.next = False    def connectionMade(self):
        self.send("!nick " + self.chat.nick)
    def send(self, line):
        self.transport.write(line.encode("utf-8") + "\r\n")
    def dataReceived(self, data):
        if data.index("\r\n") != len(data) - 2:
            tmp = data.split("\r\n", 1)
            data = tmp[0]
            self.next = tmp[1]
        else:
            self.next = False
        data = data.decode("utf-8").rstrip().split(" ", 1)
        action = data[0]
        if action == "!nick":
            self.chat.nick = data[1]
            self.chat.nick_box.setText(data[1])
            if len(self.users) == 0:
                self.send("!list")
        elif action == "!list":
            argument = data[1].split()
            mode = argument[0]
            if mode == "=":
                nicks = argument[1:]
                for nick in nicks:
                    user = QtGui.QListWidgetItem(nick)
                    self.users.append(user)
                    self.chat.users_box.addItem(user)
            elif mode == "+":
                user = QtGui.QListWidgetItem(argument[1])
                self.users.append(user)
                self.chat.users_box.addItem(user)                
            elif mode == "-":
                user = self.chat.users_box.findItems(argument[1],
                    QtCore.Qt.MatchFlags(QtCore.Qt.MatchExactly))[0]
                line = self.chat.users_box.row(user)
                self.chat.users_box.takeItem(line)
                self.users.remove(user)
            elif mode == "*":
                for user in self.users:
                    if user.text().__str__() == argument[1]:
                        user.setText(argument[2])
        elif action == "!msg":
            text = time.strftime("<br>(%H:%M:%S) ") + data[1]
            self.chat.text_box.moveCursor(QtGui.QTextCursor.End)
            self.chat.text_box.insertHtml(text)
            self.chat.text_box.moveCursor(QtGui.QTextCursor.End)
            self.chat.text_box.ensureCursorVisible()
        if self.next:
            self.dataReceived(self.next)

class ClientFactory(protocol.ClientFactory):
    """ Client custom factory """
    def __init__(self, chat):
        self.chat = chat
        self.users = []
    def buildProtocol(self, addr):
        self.conn = ClientProtocol(self)
        return self.conn
    def send(self, line):
        self.conn.transport.write(line + "\r\n")
    def clientConnectionLost(self, connector, reason):
        print "Connessione persa, causa:", reason
        print "Nuovo tentativo tra 3 secondi."
        self.clean()
        task.LoopingCall(connector.connect).start(3)
    def clientConnectionFailed(self, connector, reason):
        print "Impossibile connettersi, causa:", reason
        print "Nuovo tentativo tra 3 secondi."
        self.clean()
        task.LoopingCall(connector.connect).start(3)
    def clean(self):
        for user in self.users:
            line = self.chat.users_box.row(user)
            self.chat.users_box.takeItem(line)
        self.users = []
    def nick(self):
        self.send("!nick " + self.chat.nick_box.text().toUtf8().__str__())

class Chat(QtGui.QWidget):
    """ Main widget """
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self.parent = parent
        # Return the "login name" of the user
        self.nick = getpass.getuser() # Availability: Unix, Windows.
        # Layout
        self.layout = QtGui.QGridLayout()
        # Users box widget (QListWidget) at 0, 0 (rowSpan = 2)
        self.users_box = QtGui.QListWidget()
        self.users_box.setSortingEnabled(True)
        self.users_box.setAlternatingRowColors(True)
        self.layout.addWidget(self.users_box, 0, 0, 2, 1)
        # Nick box widget (QLineEdit) at 2, 0
        self.nick_box = QtGui.QLineEdit(self.nick)
        self.nick_box.setMaxLength(32)
        self.layout.addWidget(self.nick_box, 2, 0)
        # Text box widget (QTextEdit) at 0, 1
        self.text_box = QtGui.QTextBrowser()
        self.text_box.setOpenLinks(False) # To implement link clicking
        self.text_box.setReadOnly(True)
        self.welcome = "-- <b>Benvenuto</b> in <i>Frafra Channel</i> ;)"
        self.text_box.insertHtml(self.welcome)
        self.layout.addWidget(self.text_box, 0, 1)
        # Input layout at 2, 1
        self.input_layout = QtGui.QHBoxLayout()
        # Input box (QLineEdit)
        self.input_box = QtGui.QLineEdit()
        self.input_box.setMaxLength(1024)
        self.input_layout.addWidget(self.input_box)
        # Clear input button (QPushButton)
        self.clear_input_icon = QtGui.QIcon("icons/edit-clear.png")
        self.clear_input_button = QtGui.QPushButton(self.clear_input_icon, "")
        self.clear_input_button.setFixedSize(32, 32)
        self.input_layout.addWidget(self.clear_input_button)
        # Send button (QPushButton)
        self.send_icon = QtGui.QIcon("icons/go-next.png")
        self.send_button = QtGui.QPushButton(self.send_icon, "Invia")
        self.input_layout.addWidget(self.send_button)
        # Setting up the input layout
        self.layout.addLayout(self.input_layout, 2, 1)
        # Actions bar layout at 1, 1
        self.actions = QtGui.QHBoxLayout()
        # Actions bar buttons
        buttons = (
            ("link","emblem-web", "url"),
            ("bold","format-text-bold", "b"),
            ("italic","format-text-italic", "i"),
            ("underline","format-text-underline", "u"),
            )
        for button, icon, tag in buttons:
            setattr(self, button + "_icon", QtGui.QIcon("icons/%s.png" % icon))
            setattr(self, button + "_button",
                QtGui.QPushButton(getattr(self, button + "_icon"), ""))
            button_widget = getattr(self, button + "_button")
            button_widget.setCheckable(True)
            button_widget.setFixedSize(32, 32)
            self.actions.addWidget(button_widget)
            partial = functools.partial(self.action_bar, button_widget, tag)
            self.connect(button_widget, QtCore.SIGNAL("pressed()"), partial)
        # Clear button
        self.clear_button = QtGui.QPushButton(
            QtGui.QIcon("icons/edit-clear.png"), "Pulici conversazione")
        self.actions.addWidget(self.clear_button, QtCore.Qt.AlignRight)
        self.connect(self.clear_button, QtCore.SIGNAL("pressed()"),
            self.clear_button_action)
        # Setting up the actions bar layout
        self.layout.addLayout(self.actions, 1, 1)
        # Setting columns width ratio (1:3)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 3)
        # Setting up the layout
        self.setLayout(self.layout)
        # Connecting the input and the nick boxes
        self.connect(self.input_box, QtCore.SIGNAL("returnPressed()"),
            self.input_box_action)
        self.connect(self.input_box, QtCore.SIGNAL("returnPressed()"),
            self.input_box_action)
        self.connect(self.clear_input_button, QtCore.SIGNAL("pressed()"),
            self.clear_input_action)
        self.connect(self.send_button, QtCore.SIGNAL("pressed()"),
            self.input_box_action)
        self.connect(self.nick_box, QtCore.SIGNAL("editingFinished()"),
            self.nick_box_action)
    def action_bar(self, button_widget, tag):
        """ Called when an action button is pressed """
        if not button_widget.isChecked():
            self.input_box.insert("<%s>" % tag)
        else:
            self.input_box.insert("</%s>" % tag)
        #self.input_box.setFocus(QtCore.Qt.OtherFocusReason)
    def clear_button_action(self):
        """ Called when the clear button is pressed """
        self.text_box.clear()
        self.text_box.insertHtml(self.welcome)
        self.input_box.setFocus(QtCore.Qt.OtherFocusReason)
    def clear_input_action(self):
        """ Called when the clear button is pressed """
        self.input_box.clear()
        self.input_box.setFocus(QtCore.Qt.OtherFocusReason)
    def input_box_action(self):
        """ Called when return is pressed on the input box """
        if self.input_box.text().__str__():
            text = self.input_box.text().__str__()
            jump = 0
            while "<url>" in text[jump:] and "</url>" in text[jump:]:
                start = text.index("<url>", jump)
                end = text.index("</url>", jump)
                url = text[start+5:end]
                text = text[:start] +\
                    "<a href=\"%(url)s\">%(url)s</a>" % locals() + text[end+6:]
                jump = end+6
            text = self.nick + ": " + text
            self.parent.factory.send("!msg " + text.encode("utf-8"))
            self.text_box.moveCursor(QtGui.QTextCursor.End)
            self.text_box.insertHtml(time.strftime("<br>(%H:%M:%S) ") + text)
            self.text_box.moveCursor(QtGui.QTextCursor.End)
            self.text_box.ensureCursorVisible()
            self.input_box.clear()
        self.input_box.setFocus(QtCore.Qt.OtherFocusReason)
    def nick_box_action(self):
        """ Called when the editing of the nick box is finished """
        if self.nick != self.nick_box.text().__str__():
            self.parent.factory.nick()

class Window(QtGui.QMainWindow):
    """ Main window """
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setWindowTitle("Canale Frafra")
        screen = QtGui.QDesktopWidget().screenGeometry()
        width, height = 600, 350
        self.setGeometry((screen.width() - width) / 2,
            (screen.height() - height) / 2, width, height)
        self.chat = Chat(self)
        self.setCentralWidget(self.chat)

def main():
    """ Startup code """
    window = Window()
    window.show()
    if len(sys.argv) == 2:
        if sys.argv[1] == "server":
            factory = ServerFactory(window.chat)
            reactor.listenTCP(PORT, factory)
    else:
        factory = ClientFactory(window.chat)
        reactor.connectTCP(HOST, PORT, factory)
    window.factory = factory
    reactor.runReturn()
    sys.exit(APP.exec_())

if __name__ == "__main__":
    main()

