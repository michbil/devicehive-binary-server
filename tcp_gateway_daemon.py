#!/usr/bin/env python
# -*- coding: utf8 -*-
# vim:set et tabstop=4 shiftwidth=4 nu nowrap fileencoding=utf-8:

import sys
import os
import optparse
from twisted.python import log
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
import logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import devicehive
import devicehive.auto
import devicehive.poll
from  devicehive.device.ws import WebSocketFactory
import devicehive.gateway
import devicehive.gateway.binary


import sys
from daemon import Daemon
import procname

from devicehive.gateway.binary import  *

class TcpBinaryProtocol(Protocol):
    """
    Binary protocol implementation.
    """

    def __init__(self, factory):
        #self.factory = factory
        self.packet_buffer = BinaryPacketBuffer()
        self.command_descriptors = {}
        self.notification_descriptors = {}
        self.pending_results = {}
        self.gateway = None
        self.name = None
        self.id = None

        self.registration_received = 0
        self.bad_notification_count = 0

    def dataReceived(self, data):
        """
        Method should throws events to the factory when complete packet is received
        """
        self.packet_buffer.append(data)
        while self.packet_buffer.has_packet() :
            packet = self.packet_buffer.pop_packet()
            if packet:
                self.packet_received(packet)

    def connectionLost(self, reason):
        print "Connection closed "
        return Protocol.connectionLost(self, reason)

    def makeConnection(self, transport):
        return Protocol.makeConnection(self, transport)

    def send_command(self, intent, payload):
        """
        Sends binary data into transport channel
        """
        msg = Packet(PACKET_SIGNATURE, 1, 0, intent, payload)
        bin_pkt = msg.to_binary()
        log.msg('Sending packet "{0}" into transport.'.format(' '.join([hex(ord(x)) for x in bin_pkt])))
        self.transport.write(bin_pkt)

    def connectionMade(self):
        """
        Called when connection is made. Right after channel has been established gateway need to
        send registration request intent to device(s).
        """
        print "New protocol connection made"
        pkt = RegistrationRequestPacket()
        self.transport.write(pkt.to_binary())

    """ this methods were moved from binaryfactory to binary protocol to allow serving multiple binary connections """

    class _DescrItem(object):
        def __init__(self, intent = 0, name = None, cls = None, info = None):
            self.intent = intent
            self.name = name
            self.cls = cls
            self.info = info

    def packet_received(self, packet):
        log.msg('Data packet {0} has been received from device channel'.format(packet))
        if packet.intent == SYS_INTENT_REGISTER :
            regreq = BinaryFormatter.deserialize(packet.data, RegistrationPayload)
            self.registration_received = 1;
            self.handle_registration_received(regreq)
        elif packet.intent == SYS_INTENT_REGISTER2:
            regreq = BinaryFormatter.deserialize_register2(packet.data[2:])
            self.registration_received=1;
            self.handle_registration_received(regreq)
        elif packet.intent == SYS_INTENT_NOTIFY_COMMAND_RESULT :
            notifreq = BinaryFormatter.deserialize(packet.data, NotificationCommandResultPayload)
            self.handle_notification_command_result(notifreq)
        else:
            if not self.registration_received:
                self.bad_notification_count = self.bad_notification_count + 1
                if self.bad_notification_count == 1:
                    pkt = RegistrationRequestPacket()
                    self.transport.write(pkt.to_binary())
                    print "Retry registration"
                if self.bad_notification_count > 10:
                    print "registration not received yet"
                    self.transport.loseConnection()
            self.handle_pass_notification(packet)

    def handle_registration_received(self, reg):
        """
        Adds command to binary-serializable-class mapping and then
        calls deferred object.
        """

        self.id = str(reg.device_id)
        self.name = str(reg.device_name)

        info = CDeviceInfo(id = str(reg.device_id), \
                           key = reg.device_key, \
                           name = reg.device_name, \
                           device_class = CDeviceClass(name = reg.device_class_name, version = reg.device_class_version), \
                           equipment = [CEquipment(name = e.name, code = e.code, type = e.typename) for e in reg.equipment])
        def fill_descriptors(objs, out, info) :
            for obj in objs :
                okey = obj.intent
                if not okey in out :
                    cls = obj.descriptor()
                    out[okey] = BinaryFactory._DescrItem(obj.intent, obj.name, cls, info)
                else :
                    out[okey].intent = obj.intent
                    out[okey].name = obj.name
                    out[okey].info = info
        fill_descriptors(reg.commands, self.command_descriptors, info)
        fill_descriptors(reg.notifications, self.notification_descriptors, info)
        self.gateway.registration_received(info)

    def handle_notification_command_result(self, notification):
        """
        Run all callbacks attached to notification_received deferred
        """
        log.msg('BinaryProtocol.handle_notification_command_result')
        if notification.command_id in self.pending_results :
            deferred = self.pending_results.pop(notification.command_id)
            deferred.callback(CommandResult(notification.status, notification.result))

    def handle_pass_notification(self, pkt):
        for notif in [self.notification_descriptors[intent] for intent in self.notification_descriptors if intent == pkt.intent] :
            obj = BinaryFormatter.deserialize(pkt.data, notif.cls)
            params = obj.to_dict()
            self.gateway.notification_received(notif.info, CNotification(notif.name, params))



    def do_command(self, device_id, command, finish_deferred):
        """
        This handler is called when a new command comes from DeviceHive server.

        @type command: C{object}
        @param command: object which implements C{ICommand} interface
        """
        log.msg('A new command has came from a device-hive server to device "{0}".'.format(device_id))
        command_id = command.id
        command_name = command.command
        descrs = [x for x in self.command_descriptors.values() if x.name == command_name]
        if len(descrs) > 0 :
            log.msg('Has found {0} matching command {1} descriptor(s).'.format(len(descrs), command))
            command_desc = descrs[0]
            command_obj = command_desc.cls()
            log.msg('Command parameters {0}.'.format(command.parameters, type(command.parameters)))
            command_obj.update(command.parameters)
            self.pending_results[command_id] = finish_deferred
            self.send_command(command_desc.intent, struct.pack('<I', command_id) + BinaryFormatter.serialize_object(command_obj))
        else:
            msg = 'Command {0} is not registered for device "{1}".'.format(command, device_id)
            log.err(msg)
            finish_deferred.errback(msg)

class TcpBinaryFactory(ServerFactory):

    def __init__(self, gateway):
        #self.packet_buffer = BinaryPacketBuffer()
        #self.protocol = None
        self.gateway = gateway
        self.protocols = []

    def buildProtocol(self, addr):
        log.msg('BinaryFactory.buildProtocol')
        protocol = TcpBinaryProtocol(self)
        protocol.gateway = self.gateway

        self.protocols.append(protocol)

        return protocol

    def do_command(self, device_id, command, finish_deferred):
        for p in self.protocols:
            if p.id == device_id:
                p.do_command(device_id,command,finish_deferred)
                return



class Gateway(devicehive.gateway.BaseGateway):
    def __init__(self, url, factory_cls) :
        super(Gateway, self).__init__(url, factory_cls)
    
    def registration_received(self, device_info):
        super(Gateway, self).registration_received(device_info)
    
    def notification_received(self, device_info, notification):
        super(Gateway, self).notification_received(device_info, notification)
    
    def do_command(self, sender, command, finish_deferred):
        super(Gateway, self).do_command(sender, command, finish_deferred)
    
    def run(self, transport_endpoint, device_factory):
        super(Gateway, self).run(transport_endpoint, device_factory)

    def on_connected(self):
        super(Gateway, self).on_connected()
        #self.factory.authenticate('device', 'device')



def start():

    log.startLogging(sys.stdout)
    devicehive.poll.RequestFactory.noisy=0
    gateway = Gateway('http://kidgo.com.ua:8080/DeviceHiveJava/rest', devicehive.auto.AutoFactory)
    #gateway = Gateway('http://nn6029.pg.devicehive.com/api', devicehive.auto.PollFactory)

    # create endpoint and factory to be used to organize communication channel to device
    endpoint = TCP4ServerEndpoint(reactor, 9000)
    bin_factory = TcpBinaryFactory(gateway)
    # run gateway application
    gateway.run(endpoint, bin_factory)
    print "reactor started"
    reactor.run()




class BinTCPDaemon(Daemon):
    name   = 'bintcpd'
    site   = None
    server = None

    #--------------------------------------------------------------------------
    def __init__(self):
        Daemon.__init__(self, pidfile='/tmp/%s.pid' % (self.name.lower()) )
        procname.setprocname(self.name)

    #--------------------------------------------------------------------------
    def run(self):
        log.startLogging(open('/tmp/bintcpd.log', 'w'))

        devicehive.poll.RequestFactory.noisy=0
        gateway = Gateway('http://kidgo.com.ua:8080/DeviceHiveJava/rest', devicehive.auto.AutoFactory)

        # create endpoint and factory to be used to organize communication channel to device
        endpoint = TCP4ServerEndpoint(reactor, 9000)
        bin_factory = TcpBinaryFactory(gateway)
        # run gateway application
        gateway.run(endpoint, bin_factory)
        print "reactor started"
        reactor.run()

if __name__ == '__main__':

    daemon = 0;

    parser = optparse.OptionParser()
    parser.add_option("-d", "--daemon",
                  action="store", dest="daemon", default=False,
                  help="daemonize service")
    (options, args) = parser.parse_args()
    if options.daemon:
        daemon = BinTCPDaemon()
        daemon.start()
    else:
        start()
