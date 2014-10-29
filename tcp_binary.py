
import devicehive
import devicehive.auto
import devicehive.poll

import devicehive.gateway
import devicehive.gateway.binary
import binascii

from devicehive import BaseCommand

from devicehive.gateway.binary import  *

class BasicBinaryProtocol(Protocol):
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

        #print 'GOT:' +  binascii.b2a_hex(data)

        self.packet_buffer.append(data)
        while self.packet_buffer.has_packet() :
            packet = self.packet_buffer.pop_packet()
            if packet != None:
                self.packet_received(packet)

    def connectionLost(self, reason):
        print "Connection closed "
        return Protocol.connectionLost(self, reason)

    def makeConnection(self, transport):
        return Protocol.makeConnection(self, transport)

    def packet_received(self,packet):
        pass

    def packDWORD(self,l):
        return str(bytearray([l & 0xFF, l >> 8]))

    def packStrlen(self,str):
        return self.packDWORD(len(str))

    def packLONG(self,l):
        return str(bytearray([l & 0xFF, (l >> 8) & 0xFF,(l >> 16) & 0xFF, (l >> 24) & 0xFF]))

    def packStr(self,str):
        return self.packStrlen(str)+str

    def packPkt(self,intent,payload):
        return Packet(PACKET_SIGNATURE, 0, 0, intent, payload).to_binary()

    def sendPkt(self,pkt):
        self.transport.write(pkt)



class TcpBinaryProtocol(BasicBinaryProtocol):

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
                if self.bad_notification_count > 44440:
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
        self.gateway.registration_received(info,self)

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

import time, threading


class Gateway(devicehive.gateway.BaseGateway):
    def __init__(self, url, factory_cls) :
        super(Gateway, self).__init__(url, factory_cls)
        self.timer()

    def registration_received(self, device_info,obj):
        super(Gateway, self).registration_received(device_info,obj)

    def notification_received(self, device_info, notification):
        if notification.name=="EEB":
            notification.parameters['value'] = notification.parameters['value'].tolist()
        super(Gateway, self).notification_received(device_info, notification)
        super(Gateway, self).notification_received(device_info, notification)

    def do_command(self, sender, command, finish_deferred):
        super(Gateway, self).do_command(sender, command, finish_deferred)

    def run(self, transport_endpoint, device_factory):
        super(Gateway, self).run(transport_endpoint, device_factory)

    def on_connected(self):
        super(Gateway, self).on_connected()
        #self.factory.authenticate('device', 'device')

    def send_ping_cmd(self,id):
        command = BaseCommand()
        command.command = "PN"
        command.parameters= {"UPD":1}

        self.do_command(id,command,self.CommandCallback(self))

    class CommandCallback():
        def __init__(self,base):
            self.base = base
        def errback(self,reason):
            print "Error during ping command"
            print reason
        def callback(self,status):
            print "Ping result",status.status,status.result


    def timer(self):
        threading.Timer(10, self.timer).start()
        print ("Refresh tick")
        print self.devices

        for devkey in self.devices:
            self.send_ping_cmd(devkey)
