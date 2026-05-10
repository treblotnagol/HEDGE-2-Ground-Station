# -*- coding: utf-8 -*-

import struct
import numpy as np
import sys, os
from openpyxl import Workbook
from sk_dsp_comm.fec_conv import FECConv
from cobs import cobs

def resourcePath(relativePath):
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relativePath)


def parseSciPacket(packet):
    fmt = "<HHIfffffHHHHHHH" 
    return struct.unpack(fmt, packet)
    

def convDecode(package):
    depth=30
    cc = FECConv(('1011011', '1111001'), Depth=depth) #Rate 1/2 convolution encoder
    bits = np.unpackbits(np.frombuffer(package, dtype=np.uint8))
    bits = np.append(bits, np.zeros(depth*2)) #depth*2
    bits = bits.astype(int)
    decodedBits = cc.viterbi_decoder(bits, metric_type="hard")
    decodedBits = decodedBits.astype(np.uint8)
    decodedBits = decodedBits[:len(decodedBits)-(depth*2+6)] #6 + depth*2
    nBytes = len(decodedBits) // 8
    decodedBits = decodedBits[:nBytes*8]
    package = np.packbits(decodedBits).tobytes()
    return package


def processPacket(packet):
    values = ''
    if len(packet)>0:
        dd = convDecode(packet).strip(b'\x00')
        uncobbed = cobs.decode(dd)
        values = parseSciPacket(uncobbed)
        print(values)
    return values


def writeData(data, path):
    wb = Workbook()
    ws = wb.active
    headers = ["Sequence #", "Packet Type", "GPS Epoch", 
              "Latitude", "Longitude", "H. Speed (m/s) ", "V. Speed (m/s)",
              "Altitude (km)", "Time (ms)", "Temp1 (C)", "Temp2 (C)",
              "Temp3 (C)", "Temp4 (C)", "Press1 (kPa)", "Press2 (kPa)"]
    ws.append(headers)
    for row in data:
        if len(row)>0:
            ws.append(row)

    wb.save(path)