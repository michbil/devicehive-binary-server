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


try:
    import procname
except ImportError:
    pass

from devicehive.gateway.binary import  *

from tcp_binary import *


devicehive.auto.PollFactory.noisy=0

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
