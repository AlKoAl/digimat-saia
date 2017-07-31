import struct
import time

from ModbusDataLib import bin2boollist
from ModbusDataLib import boollist2bin


# This is the precalculated hash table for CCITT V.41.
SAIASBusCRCTable = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
    0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
    0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
    0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
    0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
    0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
    0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
    0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
    0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
    0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
    0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
    0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
    0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
    0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
    0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
    0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
    0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
    0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
    0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
    0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
    0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
    0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
    0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0
]


def SAIASBusCRC(inpdata):
    """Calculate a CCIT V.41 CRC hash function based on the polynomial
        X^16 + X^12 + X^5 + 1 for SAIA S-Bus (initializer = 0x0000)
    Parameters: inpdata (string) = The string to calculate the crc on.
    Return: (integer) = The calculated CRC.
    """
    # This uses the built-in reduce rather than importing it from functools
    # in order to provide compatiblity with Python 2.5. This may have to be
    # changed in future for Python 3.x
    return reduce(lambda crc, newchar:
        SAIASBusCRCTable[((crc >> 8) ^ ord(newchar)) & 0xFF] ^ ((crc << 8) & 0xFFFF),
            inpdata, 0x0000)


class SAIARequest(object):

    COMMAND_READ_FLAGS = 0x02
    COMMAND_READ_INPUTS = 0x03
    COMMAND_READ_OUTPUTS = 0x05
    COMMAND_READ_REGISTERS = 0x06
    COMMAND_WRITE_FLAGS = 0x0b
    COMMAND_WRITE_OUTPUTS = 0x0c
    COMMAND_WRITE_REGISTERS = 0x0d
    COMMAND_READ_STATIONNUMBER = 0x1d

    def __init__(self, link, retry=3):
        self._link=link
        self._retry=retry
        self._data=None
        self._command=0
        self._stamp=0
        self._ready=False
        self._sequence=0
        self.onInit()

    def onInit(self):
        pass

    def setup(self):
        self.validate()

    @property
    def link(self):
        return self._link

    @property
    def server(self):
        return self.link.server

    @property
    def memory(self):
        return self.server.memory

    @property
    def logger(self):
        return self.link.logger

    def initiate(self):
        return self.link.initiate(self)

    def safeMakeArray(self, item):
        if type(item) in (list, tuple):
            return item

        items=[]
        if item:
            items.append(item)
        return items

    def safeMakeBoolArray(self, item):
        items=self.safeMakeArray()
        return map(bool, items)

    def createFrameWithPayload(self, payload=None):
        """
        Add hedear (data size) and footer (crc) to the given data
        plus typical frame attributes
        """

        # Typical Request Format
        # ----------------------
        # frame length,
        # protocol number (0,1), protocol type (0), frame type (0=REQ, 1=RESP, 2=ACK/NAK),
        # station address, command
        # [data]
        # crc

        if payload:
            sizePayload=len(payload)
            fformat='>L BBHB BB %ds' % sizePayload
            fsize=13+sizePayload
            frame=struct.pack(fformat,
                fsize,
                0, 0, self._sequence, 0,
                self.server.lid, self._command,
                payload)
        else:
            fformat='>L BBHB BB'
            fsize=13
            frame=struct.pack(fformat,
                fsize,
                0, 0, self._sequence, 0,
                self.server.lid, self._command)

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
                self._sequence=self.link.generateMsgSeq()
                self._data=self.createFrameWithPayload(self.encode())
                self._stamp=time.time()
            else:
                self.logger.error('%s:unable to encode (not ready)' % self.__class__)
                return None
        except:
            self.logger.exception('request:build()')
        return self._data

    @property
    def data(self):
        if self._data:
            return self._data
        return self.build()

    def age(self):
        return time.time()-self._stamp

    def consumeRetry(self):
        if self._retry>0:
            self._retry-=1
            self._stamp=time.time()
            return True

    def validateMessage(self, sequence, payload=None):
        if self.isReady():
            if sequence==self._sequence:
                return True

    def processResponse(self, payload):
        return False

    def onSuccess(self):
        pass

    def onFailure(self):
        pass

    def data2uint32list(self, data):
        return list(struct.unpack('>%dI' % (len(data) / 4), data))


class SAIARequestReadStationNumber(SAIARequest):
    def onInit(self):
        self._command=SAIARequest.COMMAND_READ_STATIONNUMBER
        self.ready()

    def encode(self):
        return None

    def processResponse(self, payload):
        lid=int(payload[0])
        print "RECEIVED LID", lid
        self.server.setLid(lid)
        return True

    def onFailure(self):
        print "DEBUG: Simulate LID rx"
        self.server.setLid(1)


class SAIARequestReadItem(SAIARequest):
    def setup(self, address, count=1):
        self._address=address
        self._count=count
        self.ready()

    def encode(self):
        # count = number of item to read - 1
        return struct.pack('>BH',
                self._count-1, self._address)


class SAIARequestReadFlags(SAIARequestReadItem):
    def onInit(self):
        self._command=SAIARequest.COMMAND_READ_FLAGS

    def processResponse(self, payload):
        flags=self.memory.flags

        index=self._address
        count=self._count
        values=bin2boollist(payload)
        print index, count, values

        for n in range(count):
            print "FLAG(%d)=%d" % (index+n, values[n])
            flags[index+n].setValue(values[n])

        return True


class SAIARequestWriteFlags(SAIARequest):
    def onInit(self):
        self._command=SAIARequest.COMMAND_WRITE_FLAGS

    def setup(self, address, values):
        self._address=address
        self._values=self.safeMakeBoolArray(values)
        self.ready()

    def encode(self):
        data=boollist2bin(self._values)

        # bytecount = number item to write (as msg length + 2)
        bytecount=len(data)+2
        fiocount=len(self._values)-1

        return struct.pack('>BHB %ds',  bytecount, self._address, fiocount, data)


class SAIARequestReadInputs(SAIARequestReadItem):
    def onInit(self):
        self._command=SAIARequest.COMMAND_READ_INPUTS

    def processResponse(self, payload):
        inputs=self.memory.inputs

        index=self._address
        count=self._count
        values=bin2boollist(payload)
        print index, count, values

        for n in range(count):
            print "INPUT(%d)=%d" % (index+n, values[n])
            inputs[index+n].setValue(values[n])

        return True


class SAIARequestReadOutputs(SAIARequestReadItem):
    def onInit(self):
        self._command=SAIARequest.COMMAND_READ_OUTPUTS

    def processResponse(self, payload):
        outputs=self.memory.outputs

        index=self._address
        count=self._count
        values=bin2boollist(payload)
        print index, count, values

        for n in range(count):
            print "OUTPUT(%d)=%d" % (index+n, values[n])
            outputs[index+n].setValue(values[n])

        return True


class SAIARequestWriteOutputs(SAIARequestWriteFlags):
    def onInit(self):
        self._command=SAIARequest.COMMAND_WRITE_OUTPUTS


class SAIARequestReadRegisters(SAIARequestReadItem):
    def onInit(self):
        self._command=SAIARequest.COMMAND_READ_REGISTERS

    def processResponse(self, payload):
        registers=self.memory.registers

        index=self._address
        count=self._count
        values=self.data2uint32list(payload)
        print index, count, values

        for n in range(count):
            item=registers[index+n]
            value=values[n]
            print "REGISTER(%d)=%f" % (index+n, value)
            item.setValue(value)

        return True


class SAIARequestWriteRegisters(SAIARequest):
    def onInit(self):
        self._command=SAIARequest.COMMAND_WRITE_REGISTERS

    def setup(self, address, values):
        self._address=address
        self._values=self.safeMakeArray(values)
        self.ready()

    def encode(self):
        # TODO: -----------------------
        data=listin2bin(self._values)

        # bytecount = number item to write (as msg length + 2)
        bytecount=len(data)+2
        fiocount=len(self._values)-1

        return struct.pack('>BHB %ds',  bytecount, self._address, fiocount, data)


if __name__ == "__main__":
    pass
