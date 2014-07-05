from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint

import devicehive
from devicehive.gateway.binary import *

class Greeter(Protocol):
    def sendMessage(self, pkt):
        self.transport.write(pkt)

class GreeterFactory(Factory):
    def buildProtocol(self, addr):
        return Greeter()

def gotProtocol(p):
    pdataok = Packet(PACKET_SIGNATURE, 2, 3, 4, '123').to_binary()
    pdatabad = pdataok[:len(pdataok)-1]+'\xd4'
    p.sendMessage(pdatabad)
    reactor.callLater(1, p.sendMessage, pdataok)
    #reactor.callLater(2, p.transport.loseConnection)

point = TCP4ClientEndpoint(reactor, "localhost", 9000)
d = point.connect(GreeterFactory())
d.addCallback(gotProtocol)
reactor.run()


