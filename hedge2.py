# -*- coding: utf-8 -*-
"""HEDGE-2 OBC main process.

This process retrieves science data from SCI PCB and combines it with 
GPS-derived data.  The result is framed, convolutional coded, and 
transmitted via two separate radios.
"""
import sys
import serial
import threading
import queue
import struct
import time
import gpsd
import numpy as np
from sk_dsp_comm.fec_conv import FECConv
from cobs import cobs
from ax25_funcs import create_ui_frame, send_unproto
from hexdump import hexdump

"""get_sci_data
Function to retrieve science data and put it in the queue for the main thread

...

Attributes
----------
sci_uart : UART
    the UART interface for SCI PCB
sci_queue : queue.SimpleQueue
    the queue to put the science data into
gpsd : GPSD
    the GPSD module for retrieving GPS data
stop_event : threading.Event
    an event to signal the thread to stop

The SCI PCB sends Consistent Overhead Byte Stuffing (COBS) stuffed, 
zero-terminated packets via UART5.  This function, running in a 
separate thread, reads those packets, 
removes the COBS stuffing, reads time, position, and speed data from gpsd, and 
combines the OBC-generated and the SCI-generated data into a single 
byte array.  That byte array is then COBS stuffed, and processed through a 
convolutional error correction code.  The result is placed on 
the "sci_queue" FIFO queue for further processing by the main thread.

This work is made available under a Creative Commons CC-1.0 license.
For more information, please see http://creativecommons.org/publicdomain/zero/1.0/
"""

def get_sci_data(sci_uart, sci_queue, gpsd, stop_event):
    sci_buffer = b''
    full_buffer = b''
    seq_no = 0
    packet_type_sci = 0
    fmt = "<HHIfffff"  # 2 + 4 + 4 * 4 = 22
    while not stop_event.is_set():
        packet = sci_uart.read_until(expected=b'\x00')
        if len(packet) > 0:
            sci_buffer = b''.join([sci_buffer, packet])
            if packet[-1] == 0:
                seq_no += 1
                gps_time = 0
                lat = 0.0
                lon = 0.0
                speed_h = 0.0
                speed_v = 0.0
                altitude = 0.0
                gnss = gpsd.get_current()
                if gnss.mode >= 2:
                    gps_time = round(gnss.get_time(local_time=False).timestamp())
                    speed_h = gnss.hspeed
                    speed_v = gnss.climb
                    lat = gnss.lat
                    lon = gnss.lon
                if gnss.mode >= 3:
                    altitude = gnss.alt
                uncobbed = cobs.decode(sci_buffer[:-1])
                header = struct.pack(fmt, seq_no, packet_type_sci, gps_time, lat, lon, speed_h, speed_v, altitude)
                full_buffer = cobs.encode(b''.join([header, uncobbed[5:19]])) #change back to 5:17 if it breaks code
                full_buffer = convEncode(full_buffer) #Convolution Code
                sci_queue.put_nowait(full_buffer)
                sci_buffer = b''
                full_buffer = b''


#Convolution Code algorithm, using scikit FEC convolution
def convEncode(package):
    depth = 30
    cc = FECConv(('1011011', '1111001'), Depth=depth) #Rate 1/2 convolution encoder
    bits = np.unpackbits(np.frombuffer(package, dtype=np.uint8))
    bits = np.append(bits, np.zeros(66, dtype=np.uint8))
    encodedBits,*_ = cc.conv_encoder(bits, state='000000') #K=7, NASA standard
    encodedBits = encodedBits.astype(np.uint8)
    pad = (8 - len(encodedBits) % 8) % 8
    encodedBits = np.append(encodedBits, np.zeros(pad, dtype=np.uint8))
    package = np.packbits(encodedBits).tobytes()
    return package


"""main
Process SCI and GNSS data, then transmit it via the two RF channels.

...

Attributes
----------
    None

The main thread initializes the "gpsd" connection, the two UARTs, the "sci_queue" thread-safe 
queue, and the "stop_event" thread-safe event flag.  It then starts the 
"get_sci_data" thread.  The main "while" loop retrieves packets from 
the "sci_queue" queue and transmits it via the XBee and the DMR radios.
"""

def main():
    gnssConnected = False
    gnssReady = False
    while not gnssConnected:
        try:
            gpsd.connect()
        except Exception as e:
            print(e)
            time.sleep(0.1)
            pass
        else:
            gnssConnected = True
            time.sleep(0.5)
    while not gnssReady:
        try:
            gnss = gpsd.get_current()
        except Exception as e:
            print(e)
            time.sleep(0.1)
            pass
        else:
            gnssReady = True
            time.sleep(0.5)
    sci_uart = serial.Serial(
        port='/dev/ttyAMA5', 
        baudrate=115200, 
        timeout=1
    )
    xbee_uart = serial.Serial(
        port='/dev/ttyAMA4',
        baudrate=19200,
        timeout=1
    )
    sci_queue = queue.SimpleQueue()
    stop_event = threading.Event()
    sci_thread = threading.Thread(target=get_sci_data, args=(sci_uart, sci_queue, gpsd, stop_event))
    sci_thread.start()
    try:
        while True:
            packet = b''.join([sci_queue.get(), b'\x00'])
            xbee_uart.write(packet) 
            #print(packet)
            print("Packet sent via XBee")
    #
    # Code to transmit packet via DMR AX.25 radio.  Work in progress.
    #
            if packet[0] % 10 == 0:
                try:
                    frame = create_ui_frame('KQ9P-11', 'KQ9P-11', packet)
    #                hexdump(frame)
                except (TypeError, ValueError) as e:
                    print(f'Invalid argument value: {e}')
                    sys.exit(1)
                error = send_unproto('127.0.0.1', '8001', frame)
                if error:
                    print(f'Error: {error}')
                    sys.exit(1)
                print(f'Sent packet with via DMR')

    except KeyboardInterrupt:
        stop_event.set()
        sci_thread.join()
        sys.exit()
        

if __name__ == "__main__":
    # Ensures main() only runs if executed directly, not if imported.
    sys.exit(main())
