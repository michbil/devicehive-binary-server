from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint

import sys
import os
from twisted.python import log

import devicehive
from devicehive.gateway.binary import *



class generic_test_device(object):

    DEVICE_KEY          =    "WATER_F1"
    DEVICE_NAME          =   "TESTDEVICE"
    DEVICE_CLASS_NAME    =   "vending_water"
    DEVICE_CLASS_VERSION  =  "1.0"
    EQUIPMENT_LENGTH     =   2
    NOTIFICATIONS_COUNT =    1
    COMMANDS_COUNT    =      1
    NPEQ_COUNT       =       2
    LED_CMD_COUNT    =       1


    DEVICE_ID       =        "2231be97-4677-4a57-aab1-895639af8bd5"

    EQ_LEVEL    =         "LVL";
    EQ_VOLUME   =        "VLM";
    EQ_TEMP     =         "TMP";
    EQ_CNT      =        "CNT";
    EQ_MONEY    =         "MNY";
    EQ_LITER_INCASS=      "INL";
    EQ_ERRORS       =     "ERR";
    EQ_FLAGS       =      "FLG";
    EQ_ADC_VOLTS   =      "ADC";
    EQ_FROM_FULL   =      "FFU";

    NTF_EEBLOCK = "EEB";
    NTF_LOGLINE = "LL";

    CMD_CLEARERRORS = "CLE";
    CMD_READEEPROM = "REE";
    CMD_WRITEEPROM = "WEE";
    CMD_RESET = "RST";
    CMD_SERVICEMODE = "SM";

    MIN_CUSTOM_INTENT=256
    D2G_EQUIPMENT=(MIN_CUSTOM_INTENT)

    level = None



    def __init__(self, name, id):
        self.DEVICE_NAME = name
        self.DEVICE_ID = id
        self.registration = "{" +\
        "id:\"" + self.DEVICE_ID + "\"," +\
        "key:\"" + self.DEVICE_KEY + "11\","  +\
        "name:\"" + self.DEVICE_NAME +"\","+\
        "deviceClass:{"+\
        "name:\"" +self.DEVICE_CLASS_NAME+"\","+\
        "version:\""+ self.DEVICE_CLASS_VERSION+ "\"},"+\
        "equipment:["+\
        "{code:\"" + self.EQ_LEVEL + "\",name:\"" + self.EQ_LEVEL + "\",type:\"" + self.EQ_LEVEL + "\"},"+\
        "{code:\""+self.EQ_VOLUME+ "\",name:\"" +self.EQ_VOLUME+ "\",type:\"" +self.EQ_VOLUME+ "\"},"+\
        "{code:\"" +self.EQ_CNT+ "\",name:\"" +self.EQ_CNT+ "\",type:\"" +self.EQ_CNT+ "\"},"+\
        "{code:\"" +self.EQ_TEMP+ "\",name:\"" +self.EQ_TEMP+ "\",type:\"" +self.EQ_TEMP+ "\"},"+\
        "{code:\"" +self.EQ_ERRORS+ "\",name:\"" +self.EQ_ERRORS+ "\",type:\"" +self.EQ_ERRORS+ "\"},"+\
        "{code:\"" +self.EQ_MONEY+ "\",name:\"" +self.EQ_MONEY+ "\",type:\"" +self.EQ_MONEY+ "\"},"+\
        "{code:\"" +self.EQ_FLAGS+ "\",name:\"" +self.EQ_FLAGS+ "\",type:\""+self.EQ_FLAGS+"\"},"+\
        "{code:\"" +self.EQ_LITER_INCASS+ "\",name:\""+self.EQ_LITER_INCASS+ "\",type:\""+ self.EQ_LITER_INCASS+ "\"},"+\
        "{code:\"" +self.EQ_ADC_VOLTS+ "\",name:\""+self.EQ_ADC_VOLTS+"\",type:\"VOLTAGE PRESSURE\"},"+\
        "{code:\"" +self.EQ_FROM_FULL+ "\",name:\""+self.EQ_FROM_FULL+"\",type:\"LITERS SINCE FULL\"}"+\
        "],"+\
        "commands:["+\
        "{intent:257,name:\"" +self.CMD_CLEARERRORS+ "\",params:{}},"+\
        "{intent:258,name:\"" +self.CMD_READEEPROM+ "\",params:{adr:u16}},"+\
        "{intent:261,name:\"" +self.CMD_WRITEEPROM+ "\",params:{adr:u16,value:u8}},"+\
        "{intent:262,name:\"" +self.CMD_RESET+ "\",params:{}},"+\
        "{intent:263,name:\"" +self.CMD_SERVICEMODE+ "\",params:{enter:u8,pass:str}},"+\
        "{intent:264,name:\"" + "PN" + "\",params:{upd:u8}},"+\
        "],"+\
        "notifications:["+\
        "{intent:256,name:\"equipment\",params:{equipment:str,value:u32}},"+\
        "{intent:259,name:\"" +self.NTF_EEBLOCK+ "\",params:{adr:u16,value:[u8]}},"+\
        "{intent:260,name:\"" +self.NTF_LOGLINE+ "\",params:{line:str}}"+\
        "]"+\
        "}"

    def sendDWORD(self,l):
        return str(bytearray([l & 0xFF, l >> 8]))
    def sendStrlen(self,str):
        return self.sendDWORD(len(str))
    def sendLONG(self,l):
        return str(bytearray([l & 0xFF, (l >> 8) & 0xFF,(l >> 16) & 0xFF, (l >> 24) & 0xFF]))

    def sendStr(self,str):
        return self.sendStrlen(str)+str

    def sendRegistration(self):
        print self.registration
        return Packet(PACKET_SIGNATURE, 0, 0, 3, self.sendStr(self.registration)).to_binary()

    def sendEquipmentLong(self,eq,value):
        return Packet(PACKET_SIGNATURE, 0, 0, self.D2G_EQUIPMENT, self.sendStr(eq)+self.sendLONG(value)).to_binary()

proto = None

class DevModel():

    def __init__(self):
        self.volume = 10
        self.level = 12
        self.temp = 27.1
        self.adc = 0.6
        self.counter = 334
        self.fromfull = 42
        self.flags = 0
        self.incass_liters = 45
        self.money_incass = 33
        self.errors = 0


    def send_vars(self, device):

        pkt = device.sendEquipmentLong(device.EQ_LEVEL, self.level)
        pkt = pkt + device.sendEquipmentLong(device.EQ_VOLUME, self.volume )
        pkt = pkt + device.sendEquipmentLong(device.EQ_TEMP, int(self.temp*10))
        pkt = pkt + device.sendEquipmentLong(device.EQ_CNT,self.counter)
        pkt = pkt + device.sendEquipmentLong(device.EQ_MONEY, self.money_incass)
        pkt = pkt + device.sendEquipmentLong(device.EQ_LITER_INCASS, self.incass_liters)
        pkt = pkt + device.sendEquipmentLong(device.EQ_ERRORS,self.errors)
        pkt = pkt + device.sendEquipmentLong(device.EQ_FLAGS,self.flags)
        pkt = pkt + device.sendEquipmentLong(device.EQ_ADC_VOLTS, int(self.adc*100))
        pkt = pkt + device.sendEquipmentLong(device.EQ_FROM_FULL, self.fromfull)

        return pkt

    def process_values_with_time(self):
        pass


class Greeter(Protocol):

    device = None
    level = None

    def __init__(self):
        self.model = DevModel()

    def sendMessage(self, pkt):
        print "sending message " + pkt
        self.transport.write(pkt)
        pkt = self.model.send_vars(self.device)
        #reactor.callLater(3, self.sendMessage, pkt)

    def connectionMade(self):
        print "Sending registartion"
        pdataok = self.device.sendRegistration()


        #pdatabad = pdataok[:len(pdataok)-1]+'\xd4'
        #p.sendMessage(pdatabad)
        reactor.callLater(2, self.sendMessage, pdataok)

class GreeterFactory(Factory):

    uids = ["2201be97-4677-4a57-aab1-895639af8bd5","2501be97-4677-4a57-aab1-895639af8bd5"]
    names = ["TESTDEVICE1","TESTDEVICE2"]
    levels = [4440,5550]

    devices_added = 0

    def buildProtocol(self, addr):
        p = Greeter()
        p.device = generic_test_device(self.names[self.devices_added], self.uids[self.devices_added])
        p.level = self.levels[self.devices_added]
        self.devices_added = self.devices_added + 1
        return p


def gotProtocol(p):

    global proto
    proto = p

        #reactor.callLater(5, p.transport.loseConnection)

log.startLogging(sys.stdout)


gf = GreeterFactory()

#point = TCP4ClientEndpoint(reactor, "kidgo.com.ua", 9000)
#d = point.connect(gf)

point = TCP4ClientEndpoint(reactor, "localhost", 9000)
d = point.connect(gf)

reactor.run()
