import struct

from .ModbusDataLib import boollist2bin

from .request import SAIASBusCRC

SAIA_CPU_TYPE = 'XXDIG'
SAIA_FW_VERSION = '001'


class SAIAReply(object):

    REPLY_TYPE_RESPONSE = 1
    REPLY_TYPE_ACKNAK = 2

    def __init__(self, node, sequence):
        self._node=node
        self._sequence=sequence
        self._replyType=None
        self._data=None
        self._ready=False
        self.onInit()

    def onInit(self):
        pass

    @property
    def node(self):
        return self._node

    @property
    def memory(self):
        return self.node.server.memory

    @property
    def logger(self):
        return self.node.logger

    def setReplyTypeResponse(self):
        self._replyType=SAIAReply.REPLY_TYPE_RESPONSE

    def setReplyTypeAckNak(self):
        self._replyType=SAIAReply.REPLY_TYPE_ACKNAK

    def createFrameWithPayload(self, payload):
        """
        Add hedear (data size) and footer (crc) to the given data
        plus typical frame attributes
        """

        # Typical Request Format
        # ----------------------
        # frame length,
        # protocol number (0,1), protocol type (0), sequence, frame type (0=REQ, 1=RESP, 2=ACK/NAK),
        # [data]
        # crc

        sizePayload=len(payload)
        fformat='>L BBHB %ds' % sizePayload
        fsize=11+sizePayload
        frame=struct.pack(fformat,
            fsize,
            0, 0, self._sequence, self._replyType,
            payload)

        return struct.pack('>%ds H' % len(frame), frame, SAIASBusCRC(frame))

    def encode(self):
        """
        create binary data frame from request data
        header (size) and footer (crc) will be added around this
        """
        return None

    def ready(self):
        self._ready=True

    def isReady(self):
        if self._ready:
            return True

    def build(self):
        try:
            if self.isReady():
                self._data=self.createFrameWithPayload(self.encode())
            else:
                self.logger.error('%s:unable to encode (not ready)' % self.__class__)
                return None
        except:
            self.logger.exception('%s:build()' % self.__class__)
        return self._data

    @property
    def data(self):
        if self._data:
            return self._data
        return self.build()

    def hexdata(self):
        sdata=' '.join(x.encode('hex') for x in self.data)
        return sdata


class SAIAResponseReadStationNumber(SAIAReply):
    def onInit(self):
        self.setReplyTypeResponse()
        self.ready()

    def encode(self):
        return struct.pack('>B', self.node._lid)


class SAIAResponseReadPcdStatusOwn(SAIAReply):
    def onInit(self):
        self.setReplyTypeResponse()
        self.ready()

    def encode(self):
        # return 'RUN'
        return struct.pack('>B', 0x52)


class SAIAResponseReadProgramVersion(SAIAReply):
    def onInit(self):
        self.setReplyTypeResponse()
        self.setup(SAIA_CPU_TYPE, SAIA_FW_VERSION)

    def setup(self, cputype=SAIA_CPU_TYPE, fwversion=SAIA_FW_VERSION):
        self._cputype=cputype
        self._fwversion=fwversion
        self.ready()

    def encode(self):
        return struct.pack('5s4s', self._cputype, self._fwversion)


class SAIAResponseReadSystemInformation(SAIAReply):
    def onInit(self):
        self.setReplyTypeResponse()

    def setup(self, sysinfo0=0, sysinfo1=0):
        self._sysinfo0=sysinfo0
        self._sysinfo1=sysinfo1
        self.ready()

    def encode(self):
        return struct.pack('>BB', 1, 0x0)


class SAIAResponseReadFlags(SAIAReply):
    def onInit(self):
        self.setReplyTypeResponse()

    def setup(self, address, count):
        if address>=0 and count>0 and count<=32:
            self._address=address
            self._count=count
            self.ready()

    def encode(self):
        flags=self.memory.flags
        values=[]

        for n in range(self._count):
            values.append(flags[self._address+n].value)

        data=boollist2bin(values)
        return struct.pack('>%ds' % len(data), data)


class SAIAResponseACK(SAIAReply):
    def onInit(self):
        self.setReplyTypeAckNak()
        self.ready()

    def encode(self):
        return struct.pack('>H', 0)


class SAIAResponseNAK(SAIAReply):
    def onInit(self):
        self.setReplyTypeAckNak()
        self.setup(1)

    def setup(self, nakcode):
        if nakcode>0:
            self._nakcode=nakcode
            self.ready()

    def encode(self):
        self.logger.error('NAK!')
        return struct.pack('>H', self._nakcode)
