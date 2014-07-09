from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint

import sys
import os
from twisted.python import log

import devicehive
from devicehive.gateway.binary import *



class generic_test_device(object):

    DEVICE_KEY          =    "TESTKEY"
    DEVICE_NAME          =   "TESTDEVICE"
    DEVICE_CLASS_NAME    =   "vending_water"
    DEVICE_CLASS_VERSION  =  "1.0"
    EQUIPMENT_LENGTH     =   2
    NOTIFICATIONS_COUNT =    1
    COMMANDS_COUNT    =      1
    NPEQ_COUNT       =       2
    LED_CMD_COUNT    =       1


    DEVICE_ID       =        "2201be97-4677-4a57-aab1-895639af8bd5"

    NP_EQUIPMENT=            "equipment"
    NP_STATE     =           "state"
    NOTIFY_EQUIPMENT    =    "equipment"
    LED_CMD_NAME     =       "UpdateLedState"

    LEVEL_EQP_NAME    =        "LEVEL"
    LEVEL_EQP_CODE   =         "LEVEL"
    LEVEL_EQP_TYPE   =         "TANK LEVEL"
    VOLUME_EQP_NAME  =          "VOLUME_S"
    VOLUME_EQP_CODE  =          "VOLUME_S"
    VOLUME_EQP_TYPE  =          "TANK VOLUME"

    TEMP_EQP_NAME   =         "TEMP"
    TEMP_EQP_CODE  =          "TEMP"
    TEMP_EQP_TYPE  =          "Temperatuer sensor"

    CNT_EQP_NAME    =        "COUNTER"
    CNT_EQP_CODE  =          "COUNTER"
    CNT_EQP_TYPE   =         "OVERALL COUNTER"

    MONEY_EQP_NAME   =         "MONEY_IN"
    MONEY_EQP_CODE   =         "MONEY_IN"
    MONEY_EQP_TYPE   =         "MONEY AFTER INCASS"

    LITER_INCASS_EQP_NAME =    "LITER_INCASS"
    LITER_INCASS_EQP_CODE =    "LITER_INCASS"
    LITER_INCASS_EQP_TYPE  =   "LITERS AFTER INCASS"

    ERRORS_EQP_NAME    =        "ERRORS"
    ERRORS_EQP_CODE     =       "ERRORS"
    ERRORS_EQP_TYPE      =      "ERRORS"

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
        "{code:\""+ self.LEVEL_EQP_CODE +"\",name:\""+ self.LEVEL_EQP_NAME+ "\",type:\"" +self.LEVEL_EQP_TYPE+ "\"},"+\
        "{code:\""+ self.VOLUME_EQP_CODE+ "\",name:\"" +self.VOLUME_EQP_NAME+ "\",type:\""+ self.VOLUME_EQP_TYPE+ "\"},"+\
        "{code:\""+ self.CNT_EQP_CODE +"\",name:\"" +self.CNT_EQP_NAME+ "\",type:\"" +self.CNT_EQP_TYPE+ "\"},"+\
        "{code:\""+ self.TEMP_EQP_CODE+ "\",name:\"" +self.TEMP_EQP_NAME+ "\",type:\""+ self.TEMP_EQP_TYPE+ "\"},"+\
        "{code:\""+ self.ERRORS_EQP_CODE +"\",name:\""+ self.ERRORS_EQP_NAME+ "\",type:\"" +self.ERRORS_EQP_TYPE +"\"},"+\
        "{code:\""+ self.MONEY_EQP_CODE +"\",name:\"" +self.MONEY_EQP_NAME+ "\",type:\""+ self.MONEY_EQP_TYPE+ "\"},"+\
        "{code:\""+ self.LITER_INCASS_EQP_CODE+ "\",name:\""+ self.LITER_INCASS_EQP_NAME+ "\",type:\"" +self.LITER_INCASS_EQP_TYPE+ "\"}"+\
        "],"+\
        "commands:["+\
        "{intent:257,name:\"ClearErrors\",params:{}},"+\
        "{intent:258,name:\"ReadEeprom\",params:{adr:u16}}"+\
        "],"+\
        "notifications:["+\
        "{intent:256,name:\"equipment\",params:{equipment:str,value:u32}},"+\
        "{intent:259,name:\"eeblock\",params:{adr:u16,values:[u8]}}"+\
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
        return Packet(PACKET_SIGNATURE, 0, 0, 3, self.sendStr(self.registration)).to_binary()

    def sendEquipmentLong(self,eq,value):
        return Packet(PACKET_SIGNATURE, 0, 0, self.D2G_EQUIPMENT, self.sendStr(eq)+self.sendLONG(value)).to_binary()

proto = None

class Greeter(Protocol):

    device = None
    level = None

    def sendMessage(self, pkt):
        print "sending message "+pkt
        self.transport.write(pkt)
        reactor.callLater(3, self.sendMessage, self.device.sendEquipmentLong(self.device.LEVEL_EQP_CODE, self.level))

    def connectionMade(self):
        #pdataok = self.device.sendRegistration()
        pdataok=""

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

point = TCP4ClientEndpoint(reactor, "localhost", 9000)
d = point.connect(gf)

point = TCP4ClientEndpoint(reactor, "localhost", 9000)
d = point.connect(gf)

reactor.run()
