
import devicehive
import devicehive.auto
import devicehive.poll
import pprint
import devicehive.gateway
import devicehive.gateway.binary
from twisted.internet import *


from tcp_gateway_daemon import TcpBinaryFactory

import pprint
from serial import PARITY_NONE
from serial import STOPBITS_ONE
from serial import EIGHTBITS
from devicehive.gateway import *
from devicehive import BaseCommand

from zope.interface import Interface, Attribute, implements


class BinaryBuffer:

    def __init__(self):
        self.buffer = []

    def append(self,data):
        self.buffer = self.buffer + data
    
    def read(self, adr): 
        return self.buffer[adr]
    
    def write(self, adr, value): 
        self.buffer[adr] = value & 0xFF
    
    def read_uint8(self, adr): 
        return self.read(adr)
    
    def write_uint8(self,adr, value):
        self.write(adr, value)

    def read_uint16(self,adr):    
        return self.read(adr) + (self.read(adr+1) << 8)
    
    def write_uint16(self,adr,value):
    
        self.write(adr,value & 0xFF) 
        self.write(adr+1,(value >> 8) & 0xFF)

    
    def read_int16(self, adr):
        sign = self.read(adr+1) & 0x80
        if sign:
            return ((self.read(adr) + (self.read(adr+1) << 8)) ^ 0xFFFF) - 1
        else:
            return self.read(adr) + (self.read(adr+1) << 8)

    
    def write_int16(self, adr, value):
    
        if value < 0:
            value = ((-value) ^ 0xFFFF)+1

        self.write(adr,value & 0xFF)
        self.write(adr+1,(value >> 8) & 0xFF)
    
    def read_uint32(self,adr):
        return self.read(adr) + (self.read(adr+1) << 8) + (self.read(adr+2) << 16)+ (self.read(adr+3) << 24)

    def read_uint32_be(self, adr):
        return self.read(adr+3) + (self.read(adr+2) << 8) + (self.read(adr+1) << 16)+ (self.read(adr) << 24)

    def write_uint32(self,adr,value):
    
        self.write(adr,value & 0xFF)
        self.write(adr+1,(value >> 8) & 0xFF);
        self.write(adr+2,(value >> 16) & 0xFF);
        self.write(adr+3,(value >> 24) & 0xFF);

    def write_int32(self, adr,value):
        self.write_uint32(adr,value);
    
    def read_int32(self, adr):
        sign = 0;
        if sign:
            return -1* (self.read(adr) + (self.read(adr+1) << 8) + (self.read(adr+2) << 16)+ ((self.read(adr+3) << 24)&0x7F))
        else:
            return self.read(adr) + (self.read(adr+1) << 8) + (self.read(adr+2) << 16)+ (self.read(adr+3) << 24)

    
    def readString(self, adr, len):
        s = ""
        for i in range(0, len-1):
            c = self.read(adr+i)
            if c==0:
                break;
            s = s + chr(c)
        return s;

    
    def writeString(self, adr, str, leng):
        if len(str) > leng:
            return
        leng = len(str)
        i=0
        for i in range(0,leng-1):
            self.write(adr+i,ord(str[i]))
        self.write(adr+i+1,0)

    
    def calc_checksum(self,start,end):
        cs = 0
        for i in range(start, end):
            c = self.read(i)
            cs += c

        return cs

    
    def parse_contents(self):

        TOTAL_REPEATS= 10
        COUNTER_LEN= 5

        EEADDR_LAST_ICASSATION1= 0x34
        EEADDR_LAST_ICASSATION2= 0x38

        EEADDR_MONEY= 0x40
        EEADDR_OFFSET= 0x80
        EEADDR_INCASSATIONS= 0x90
        NUM_INCASSATIONS= 10
        EEADDR_LOWER_LIMIT= 0x100
        EEADDR_LOWER_LIMIT_COPY= 0x104
        EEADDR_CALIBRATE_ENDPOINT= 0x108
        EEADDR_VENDING_LOCK= 0x109
        EEADDR_MAX_LEVEL= 0x110
        EEPROM_CONFIG_ADR= 0x130


        counter_mul = 0
        counter_add = counter_mul + 4
        pressure_zero = counter_add + 4

        temp1_on = pressure_zero + 1
        temp1_off = temp1_on + 2
        temp2_on = temp1_off + 2
        temp2_off = temp2_on + 2

        volume_50 = temp2_off + 2
        volume_100 = volume_50 + 4
        volume_150 = volume_100 + 4
        volume_200 = volume_150 + 4
        volume_250 = volume_200 + 4
        volume_300 = volume_250 + 4

        maxmoney = volume_300 + 4
        allowmany = maxmoney + 2

        GUID = allowmany + 1
        NAME = GUID + 40

        checksum = NAME + 40
        len = checksum + 4

        INC_SZ = 13


        print "Counter coef",
        print self.read_uint32(EEPROM_CONFIG_ADR + counter_mul)
        print "Counter add",
        print float(self.read_uint32(EEPROM_CONFIG_ADR + counter_add)) / 1000000.0
        print "Pressure sensor zero",
        print float(self.read_uint8(EEPROM_CONFIG_ADR + pressure_zero))*5.0/1024.0

        print "T on",
        print float(self.read_uint16(EEPROM_CONFIG_ADR + temp1_on))/10.0
        print "T off",
        print self.read_uint16(EEPROM_CONFIG_ADR + temp1_off)/10.0

        print "T on",
        print self.read_uint16(EEPROM_CONFIG_ADR + temp2_on)/10.0
        print "T off",
        print self.read_uint16(EEPROM_CONFIG_ADR + temp2_off)/10.0

        print "Price 0.50",
        print self.read_int32(EEPROM_CONFIG_ADR + volume_50)/ 1000000.0
        print "Price 1.00",
        print self.read_int32(EEPROM_CONFIG_ADR + volume_100) / 1000000.0
        print "Price 1.50",
        print self.read_int32(EEPROM_CONFIG_ADR + volume_150) / 1000000.0
        print "Price 2.00",
        print self.read_int32(EEPROM_CONFIG_ADR + volume_200) / 1000000.0
        print "Price 2.50",
        print self.read_int32(EEPROM_CONFIG_ADR + volume_250) / 1000000.0
        print "Price 3.00",
        print self.read_int32(EEPROM_CONFIG_ADR + volume_300) / 1000000.0

        print "Maxmoney",
        print self.read_uint16(EEPROM_CONFIG_ADR + maxmoney)/10.0
        print "alllowmany",
        print self.read_uint8(EEPROM_CONFIG_ADR + allowmany)

        print "GUID: ",
        print self.readString(EEPROM_CONFIG_ADR+GUID,40)
        print "NAME: ",
        print self.readString(EEPROM_CONFIG_ADR+NAME,40)

        cs1 =  self.read_uint32(EEPROM_CONFIG_ADR+checksum)
        cs2 =  self.calc_checksum(EEPROM_CONFIG_ADR, EEPROM_CONFIG_ADR+checksum)

        if cs1 == cs2:
            print "Checksum ok"

            s = raw_input("")
            self.writeString(EEPROM_CONFIG_ADR+GUID,s,40)

        else:
            print "Checksum failed"



class DummyGateway:
    implements(IGateway)

    id = ""
    device_factory = None
    addr=0

    eedata = BinaryBuffer()

    read_finished=0



    def process_data(self):
        print self.eedata
        pass

    def send_read_cmd(self):
        command = BaseCommand()
        command.command = "REE"
        command.parameters= {"adr":self.addr}

        def fail(reason):
            print "Error during command"
            print reason

        def succ(status):
            print status.status,status.result
            self.addr=self.base.addr+16
            if self.addr < 1024:
                self.send_read_cmd()
            else:
                self.read_finished=1;

        result_proto = Deferred()
        result_proto.addCallbacks(succ,fail)

        self.do_command(self.id,command,result_proto)

    def send_write_cmd(self):
        command = BaseCommand()
        command.command = "WEE"

        l=[self.eedata[self.addr:self.addr+16] for x in xrange(0, len(self.eedata), 16)]

        command.parameters= {"adr":self.addr,"data":l}

        def fail(reason):
            print "Error during command"
            print reason

        def succ(status):
            print status.status,status.result
            self.addr=self.addr+16
            if self.addr < 1024:
                self.send_write_cmd()
            else:
                self.read_finished=1;

        result_proto = Deferred()
        result_proto.addCallbacks(succ,fail)

        self.do_command(self.id,command,result_proto)

    def send_ping_cmd(self):
        command = BaseCommand()
        command.command = "PN"
        command.parameters= {"UPD":1}

        self.do_command(self.id,command,None)



    def registration_received(self, info):
        """
        Method is called when new registration request comes from device(es).
        Method could be overridden in subclass to change device registration behaviour
        or device registration information.

        @type info: C{object}
        @param info: A device registration information. It should implemet C{IDeviceInfo} interface.
        """
        print "dummy registration received"


        attrs = vars(info)
        print ', '.join("%s: %s" % item for item in attrs.items())

        self.id = info.id

        self.addr=0
        self.send_read_cmd()



    def notification_received(self, device_info, notification):
        """
        Method is called when a device sends notification. Gateway can handle it at this point.

        @type device_info: C{object}
        @param device_info: A device information which implements C{IDeviceInfo} interface.

        @type notification: C{object}
        @param notification: A notification which was sent. It implements C{INotification} interface.
        """
        print "notification received",

        if notification.name=="EEB":
            notification.parameters['value'] = notification.parameters['value'].tolist()

        if notification.name == 'equipment':
            print notification.parameters['equipment'],
            print notification.parameters['value']
        else:
            if notification.name=="EEB":
                print notification
                print "eeprom block received "+str(notification.parameters['adr'])
                self.eedata.append(notification.parameters['value'])
                if self.read_finished:
                    self.eedata.parse_contents()
            else:
                 print notification



    def do_command(self, info, command, finish_deferred):
        """
        Method is called when devicehive sends a command to a device.

        @type info: C{object}
        @param info: C{IDeviceInfo} object which reseived a command from a protocol-factory.

        @type command: C{object}
        @param command:

        @type finish_deferred: C{Deferred}
        @param finish_deferred:
        """
        print "Making command "+command.command
        self.device_factory.do_command(info, command, finish_deferred)

dummygw = DummyGateway()
factory = TcpBinaryFactory(dummygw)
dummygw.device_factory = factory


endpoint = devicehive.gateway.binary.SerialPortEndpoint(reactor, \
                                                            'COM1', \
                                                            baudrate = 19200, \
                                                            bytesize = EIGHTBITS, \
                                                            parity = PARITY_NONE, \
                                                            stopbits = STOPBITS_ONE)
endpoint.listen(factory)




reactor.run()