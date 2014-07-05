from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint

import devicehive
from devicehive.gateway.binary import *

class Greeter(Protocol):
    def sendMessage(self, msg):
        self.transport.write("MESSAGE %s\n" % msg)

class GreeterFactory(Factory):
    def buildProtocol(self, addr):
        return Greeter()

def gotProtocol(p):
    p.sendMessage("Hello")
    reactor.callLater(1, p.sendMessage, "This is sent in a second")
    reactor.callLater(2, p.transport.loseConnection)

point = TCP4ClientEndpoint(reactor, "localhost", 9000)
d = point.connect(GreeterFactory())
d.addCallback(gotProtocol)
reactor.run()


self.pkt = Packet(PACKET_SIGNATURE, 2, 3, 4, '123')