#!/usr/local/bin/python3
import sys
import socket
import string
import re


SETTINGS = {
    "host": "CHANGE THIS",
    "port": 6667,
    "nick": "CHANGE THIS",
    "ident": "CHANGE THIS",
    "realname": "Botty McBotFace",
    "master": "CHANGE THIS",
    "channel": "#CHANGETHIS",
}

def sExists(key, sdict):
    return sdict is not None and key in sdict

def cleanNick(nick):
    return re.findall('[a-zA-z0-9_\-\[\]{}\^`\|]+', nick)[0]
    
class ConSettings:
    def __init__(self, sdict):
        self.host = sdict["host"] if sExists("host", sdict) else "DefaultHost"
        self.port = sdict["port"] if sExists("port", sdict) else 6667
        self.nick = sdict["nick"] if sExists("nick", sdict)else "DefaultBot"
        self.ident = sdict["ident"] if sExists("ident", sdict) else "DefaultIdent"
        self.realname = sdict["realname"] if sExists("realname", sdict) else "Botty McBotFace"
        self.master = sdict["master"] if sExists("master", sdict) else ""
        self.bufLen = sdict["bufLen"] if sExists("bufLen", sdict) else 1024
        self.channel = sdict["channel"] if sExists("channel", sdict) else ""
        self.nickList = []

        
class CallBacks:
    def __init__(self):
        self.cb = {}
        self.set("connect", self.none)
        self.set("join", self.none)
        self.set("message", self.none)
        self.set("userjoin", self.none)
        self.set("userpart", self.none)

    def none(self, tup):
        pass

    def set(self, event, fn):
        self.cb[event] = fn
    
    def call(self, event, args):
        self.cb[event](args)

class IRCMsg:
    def __init__(self, line):
        self.nick = line[0].split("!")[0].replace(":", '')
        self.msgType = line[1] if len(line) > 1 else ""
        self.channel = line[2] if len(line) > 2 else ""
        temp = line[3:]
        self.message = [ re.sub(r"^:", '', l) for l in temp ] if len(temp) else ['']
           
class IRCConnection:
    def __init__(self, conSettings):
        self.settings = conSettings
        self.buffers = ""
        self.con = socket.socket()

    def connect(self):
        self.con.connect((self.settings.host, self.settings.port))

    def send(self, output):
        self.con.send(bytes(output + "\r\n", "UTF-8"))

    def recv(self):
        self.buffers = self.buffers + self.con.recv(self.settings.bufLen).decode("UTF-8")
        lines = self.buffers.split("\n")
        self.buffers = lines.pop()
        return lines

    
class Bot:
    def __init__(self, conSettings):
        self.callbacks = CallBacks()
        self.settings = conSettings
        self.con = IRCConnection(self.settings)

    def connect(self):
        self.con.connect()
        self.con.send("NICK {}".format(self.settings.nick))
        self.con.send("USER {} {} test: {}".format(self.settings.ident, self.settings.host, self.settings.realname))
        
    def connected(self, fn):
        self._connectCb = fn

    def write(self, target, msg):
        if target is None: target = self.settings.channel
        self.con.send("PRIVMSG {} {}".format(target, msg))

    def parse(self, line):
        line = line.rstrip()
        line = line.split()
        msg = IRCMsg(line)
        
        print(line)
        if line[0] == "ERROR": exit(1)
        # wait to receive user mode before joining channel
        if line[1] == "MODE":
            self.callbacks.call("connect", (self, msg))
            self.con.send("JOIN {}".format(self.settings.channel))
            
        #callback when bot joins the channel
        elif line[1] == "JOIN" and msg.nick == self.settings.nick:
            self.callbacks.call("join", (self, msg))
            
        elif line[1] == "JOIN":
            self.callbacks.call("userjoin", (self, msg))
            
        elif line[1] == "PART":
            self.callbacks.call("userpart", (self, msg))
            
        #reply to any pings received
        elif line[0] == "PING":
            self.con.send("PONG {}".format(line[1]))

        #received nick listing
        elif line[1] == '353':
            temp = line[5:]    
            #now add the names to the bots memory
            while len(temp):
                nick = cleanNick(temp.pop(0))
                self.settings.nickList.append(nick)

            print(self.settings.nickList)
        else:
            self.callbacks.call("message", (self, msg))

    def run(self):
        text = self.con.recv()
        for  l in text:
            self.parse(l)


def onConnect(args):
    bot = args[0]
    line = args[1]
    print("BOT CONNECTED CB")

#when the bot joins a channel
def onJoin(args):
    print("BOT JOINED CHANNEL")
    bot = args[0]
    line = args[1]
    bot.write(None, "Hello, World!")

#when a user joins the channel
def onUserJoin(args):
    bot = args[0]
    msg = args[1]
    bot.write(None, "Welcome, {}".format(msg.nick))
    
def onMessage(args):
    print("BOT READ MESSAGE")
    bot = args[0]
    ircMsg = args[1]

    #filter out any messages created by the bot itself
    if ircMsg.nick == bot.settings.nick: return

    #set the response target to channel or user depending on where it received a message from
    target = ircMsg.channel if ircMsg.channel != bot.settings.nick else ircMsg.nick
    if ircMsg.message[0] == "hello":
        bot.write(target, "Hello {}".format(ircMsg.nick))

    elif ircMsg.message[0] == "~pingall":
        string = "Hello "
        for n in bot.settings.nickList:
            string += n + ", "

        bot.write(target, string)
        
    print("Recieved msg: {} from {} in {}".format(ircMsg.message, ircMsg.nick, ircMsg.channel))

def main():
    s = ConSettings(SETTINGS)
    bot = Bot(s)
    bot.callbacks.set("connect", onConnect)
    bot.callbacks.set("join", onJoin)
    bot.callbacks.set("userjoin", onUserJoin)
    bot.callbacks.set("message", onMessage)
    bot.connect()

    while True:
        bot.run()
    

main()



    




