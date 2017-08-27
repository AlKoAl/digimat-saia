import time

# python2-3 compatibility require 'pip install future'
from queue import Queue

from .request import SAIARequestReadDBX


class SAIATransfer(object):
    def __init__(self, server):
        assert server.__class__.__name__=='SAIAServer'
        self._server=server
        self._start=False
        self._done=False
        self._timeoutWatchdog=0
        self._request=None

    @property
    def server(self):
        return self._server

    @property
    def logger(self):
        return self.server.logger

    @property
    def link(self):
        return self.server.link

    def initiateTransfer(self):
        pass

    def processDataAndContinueTransfer(self, request):
        pass

    def onSuccess(self):
        pass

    def onFailure(self):
        pass

    def isActive(self):
        if self._start:
            return True

    def isDone(self):
        if self._done:
            return True

    def heartbeat(self):
        self._timeoutWatchdog=time.time()+15.0

    def submitRequest(self, request):
        if request and not self._request:
            self._request=request
            if not self.isActive():
                self.start()

    def start(self):
        try:
            self._start=True
            self._done=False
            self.heartbeat()
            self.logger.debug('%s:start()' % self.__class__.__name__)
            self.initiateTransfer()
        except:
            self.stop(False)

    def stop(self, result=False):
        self._start=False
        self._done=True
        self.logger.debug('%s:stop(%d)' % (self.__class__.__name__, result))
        try:
            if result:
                self.onSuccess()
            else:
                self.onFailure()
        except:
            pass

    def abort(self):
        self.stop(False)

    def manager(self):
        activity=False
        if self.isActive():
            try:
                if time.time()>self._timeoutWatchdog:
                    self.logger.error('%s:watchdog()' % self.__class__.__name__)
                    self.stop(False)
                else:
                    if self._request:
                        if self._request.isDone():
                            request=self._request
                            self._request=None
                            if request.isSuccess():
                                self.processDataAndContinueTransfer(request.reply)
                                if self._request:
                                    activity=True
                                else:
                                    self.stop(True)
                            else:
                                self.stop(False)
                        else:
                            if not self._request.isActive():
                                if self.link.isIdle():
                                    self._request.initiate()
                                    activity=True
                    else:
                        self.stop(True)
            except:
                self.logger.exception('%s:onRun()' % self.__class__.__name__)
                self.stop(False)

            return activity


class SAIATransferReadDeviceInformation(SAIATransfer):
    def send(self):
        if self._count>0:
            count=min(self._maxChunkSize, self._count)
            request=SAIARequestReadDBX(self.link)
            request.setup(address=self._address, count=count)
            self.submitRequest(request)

    def initiateTransfer(self):
        self._address=0x00
        self._count=0x64
        self._maxChunkSize=0x20
        self._data=''
        self.send()

    def processDataAndContinueTransfer(self, data):
        count=len(data)/4
        self._address+=count
        self._count-=count
        self._data+=data
        self.send()

    def onSuccess(self):
        for item in self._data.split('\n'):
            try:
                (key, value)=item.split('=')
                self.server.setDeviceInfo(key.strip(), value.strip())
            except:
                pass

        #  TODO: lock #
        self.server.loadSymbols()


class SAIATransferQueue(object):
    def __init__(self, server):
        assert server.__class__.__name__=='SAIAServer'
        self._server=server
        self._queue=Queue()
        self._transfer=None

    @property
    def server(self):
        return self._server

    @property
    def logger(self):
        return self.server.logger

    def isEmpty(self):
        return self._queue.isEmpty()

    def submit(self, transfer):
        assert isinstance(transfer, SAIATransfer)
        self._queue.put(transfer)
        self.logger.debug('queue:%s', transfer.__class__.__name__)

    def getNextTransfer(self):
        try:
            return self._queue.get(False)
        except:
            pass

    def manager(self):
        activity=False
        if self._transfer:
            activity=self._transfer.manager()
            if self._transfer.isDone():
                del self._transfer
                self._transfer=None
        else:
            self._transfer=self.getNextTransfer()
            if self._transfer:
                self._transfer.start()
                activity=True
        return activity