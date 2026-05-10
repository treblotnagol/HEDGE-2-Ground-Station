# -*- coding: utf-8 -*-

import tkinter as tk
import serial
import serial.tools.list_ports
import threading
import queue
import time
import tkintermapview
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
from hedgeGSFuncs import writeData, processPacket, resourcePath

PROCESSORS = 2
STOP = None

class HedgeGS:
    def __init__(self, root):
        self.root = root
        self.root.title("HEDGE Ground Station")
        self.root.geometry("1000x700")
        self.root.iconbitmap(resourcePath("assets/icon.ico"))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.image = Image.open(resourcePath("assets/HEDGE logo.png")).resize((40,40))
        self.image = ImageTk.PhotoImage(self.image)

        self.ports = []
        self.connected = False
        self.data = []
        self.last_map_update = 0

        self.raw_queue = queue.Queue(maxsize=200)
        self.data_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.xbee = None

        self.build_ui()
        self.root.after(100, self.check_queue)


    def build_ui(self):
        # create frames
        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        self.middle_frame = tk.Frame(self.root)
        self.middle_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.bottom_frame = tk.Frame(self.root)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        #port selection
        self.port_label = tk.Label(self.bottom_frame, text="Port: ")
        self.port_label.pack(side=tk.LEFT, padx=2)
        self.port_var = tk.StringVar(value="Select Port")
        self.port_dropdown = ttk.Combobox(self.bottom_frame, textvariable=self.port_var, state="readonly", width=15)
        self.port_dropdown.pack(side=tk.LEFT, padx=2)
        self.refresh_ports()

        # Refresh button to re-scan ports
        self.refresh_btn = tk.Button(self.bottom_frame, text="⟳", command=self.refresh_ports)
        self.refresh_btn.pack(side=tk.LEFT, padx=2)

        # labels
        self.lat_label = tk.Label(self.top_frame, text="Latitude: --")
        self.lat_label.pack(side=tk.LEFT, padx=10)
        self.lon_label = tk.Label(self.top_frame, text="Longitude: --")
        self.lon_label.pack(side=tk.LEFT, padx=10)
        self.alt_label = tk.Label(self.top_frame, text="Altitude: --")
        self.alt_label.pack(side=tk.LEFT, padx=10)
        self.h_speed_label = tk.Label(self.top_frame, text="Horizontal Vel.: --")
        self.h_speed_label.pack(side=tk.LEFT, padx=10)
        self.v_speed_label = tk.Label(self.top_frame, text="Vertical Vel.: --")
        self.v_speed_label.pack(side=tk.LEFT, padx=10)
        self.logo = tk.Label(self.top_frame, image=self.image)
        self.logo.pack(side=tk.RIGHT, padx=10)

        self.paned = tk.PanedWindow(self.middle_frame, orient=tk.VERTICAL)
        self.paned.pack(fill=tk.BOTH, expand=True)
        #map
        self.map_frame = tk.Frame(self.paned, height=300)
        self.paned.add(self.map_frame)
        self.map = tkintermapview.TkinterMapView(
            self.map_frame,
            width=800,
            height=300,
            use_database_only=False,
            database_path="map_cache.db"
        )
        self.map.set_position(38.0336, -78.5080)
        self.marker = self.map.set_marker(38.0336, -78.5080)
        self.map.set_zoom(15)
        self.map.pack(fill=tk.BOTH, expand=True)
        # data table
        self.table_frame = tk.Frame(self.paned)
        self.paned.add(self.table_frame, height=200)
        self.tree = ttk.Treeview(self.table_frame, columns=(
            'seq', 'temp1', 'temp2', 'temp3', 'temp4', 'p1', 'p2'
        ), show='headings')
        # column headings
        self.tree.heading('seq', text="Seq No.")
        self.tree.heading('temp1', text="Temp 1 (°C)")
        self.tree.heading('temp2', text="Temp 2 (°C)")
        self.tree.heading('temp3', text="Temp 3 (°C)")
        self.tree.heading('temp4', text="Temp 4 (°C)")
        self.tree.heading('p1', text="Pressure 1 (kPa)")
        self.tree.heading('p2', text="Pressure 2 (kPa)")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.column('seq', width=50)
        self.tree.column('temp1', width=100)
        self.tree.column('temp2', width=100)
        self.tree.column('temp3', width=100)
        self.tree.column('temp4', width=100)
        self.tree.column('p1', width=100)
        self.tree.column('p2', width=100)
        # scrollbars
        yscrollbar = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        xscrollbar = ttk.Scrollbar(self.table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=yscrollbar.set)
        self.tree.configure(xscroll=xscrollbar.set)
        yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        xscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)
        # buttons
        self.connect_btn = tk.Button(self.bottom_frame, text="Connect", command=self.toggleConnection)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        self.status_label = tk.Label(self.bottom_frame, text="Status: Disconnected", fg="red")
        self.status_label.pack(side=tk.RIGHT, padx=10)
        self.export_btn = tk.Button(self.bottom_frame, text="Export to Excel", command=self.export_data)
        self.export_btn.pack(side=tk.RIGHT, padx=10)
        self.clear_btn = tk.Button(self.bottom_frame, text="Clear Data", command=self.clear_data)
        self.clear_btn.pack(side=tk.LEFT, padx=10)

    
    def on_close(self):
        if self.connected:
            self.toggleConnection()
        self.root.destroy()

    #port helpers
    def refresh_ports(self):
        ports = self.find_xbee_ports()
        if ports:
            self.port_dropdown['values'] = ports
            self.port_var.set(ports[0]) 
        else:
            self.port_dropdown['values'] = []
            self.port_var.set("No ports found")


    def find_xbee_ports(self):
        ports = serial.tools.list_ports.comports()
        xbee_ports = []
        for p in ports:
            if "USB Serial" in p.description or "XBee" in p.description:
                xbee_ports.append(p.device)
        return xbee_ports

    #data helpers
    def clear_data(self):
        self.tree.delete(*self.tree.get_children())
        self.data = []


    def export_data(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[
                ("Excel", "*.xlsx"),
                #("CSV File", "*.csv"),
                #("Text File", "*.txt"),
                ("All Files", "*.*")
            ]
        )
        if path:
            writeData(self.data, path)

    
    def sync_stream(self):
        ncount = 0
        while ncount<16:
            byte = self.xbee.read(1)
            if byte == b'\x00':
                ncount += 1
            else:
                ncount = 0
        
        print("Stream Synced")

    # Recevier thread function
    def readSerial(self):
        port = self.port_var.get()
        try:
            self.xbee = serial.Serial(
                port=port,
                baudrate=19200,
                bytesize=8,
                timeout=1,
                stopbits=1,
                parity="N"
            )
            print("Connected to receiver XBee on port", self.xbee.port)
            while not self.stop_event.is_set():
                try:
                    trail = b'\x00'*16
                    raw = self.xbee.read_until(trail)
                    if raw:
                        #print(raw)
                        try:
                            self.raw_queue.put_nowait(raw)
                        except:
                            print("Raw queue full: dropping packet")
                except serial.SerialException as e:
                    if not self.stop_event.is_set():
                        print(f"Serial error: {e}")
                except Exception as e:
                    print(f"Unexpected error: {e}")
        except Exception as e:
            print(f"Receiver error: {e}")
            self.root.after(0, self.toggleConnection)   # update UI on main thread
            return
        finally:
            if self.xbee and self.xbee.is_open:
                self.xbee.close()
                print("Port closed")
            for _ in range(PROCESSORS):
                self.raw_queue.put(STOP)
            print("Receiver done")

    # Processor thread function
    def parsePacket(self, num: int):
        while True:
            raw = self.raw_queue.get()

            if raw is STOP:
                self.raw_queue.task_done()
                print(f"Processor {num} shutting down")
                break

            try:
                packet = processPacket(raw)
                if packet:
                    self.data_queue.put(packet)
            except Exception as e:
                print(f"Processor {num} parse error: {e} — raw: {raw!r}")
            finally:
                self.raw_queue.task_done()

    # Display thread function
    def check_queue(self):
        latest = None
        processed = 0
        MAX = 20 # don't hog the UI thread if packets burst in
        while processed < MAX:
            try:
                packet = self.data_queue.get_nowait()
            except queue.Empty:
                break
            self.data.append(packet)
            if len(packet) >= 15:
                self.tree.insert('', tk.END, values=(
                    packet[0], packet[9], packet[10],
                    packet[11], packet[12], packet[13], packet[14]
                ))
                self.tree.yview_moveto(1)
                if len(self.tree.get_children())>(MAX*2):
                    self.tree.delete(self.tree.get_children()[0])
            latest = packet
            processed += 1

        if latest and len(latest) >= 15:
            self.lat_label.config(text=f"Latitude: {latest[3]:.4f}")
            self.lon_label.config(text=f"Longitude: {latest[4]:.4f}")
            self.alt_label.config(text=f"Altitude: {latest[7]:.1f} km")
            self.h_speed_label.config(text=f"Horizontal Vel.: {latest[5]:.4f} m/s")
            self.v_speed_label.config(text=f"Vertical Vel.: {latest[6]:.4f} m/s")
            now = time.time()
            if now - self.last_map_update > 2.0:
                self.marker.set_position(latest[3], latest[4])
                self.map.set_position(latest[3], latest[4])
                self.last_map_update = now
        self.root.after(100, self.check_queue)

    
    def toggleConnection(self):
        if self.connected: #disconnect command
            self.stop_event.set()
            if self.xbee and self.xbee.is_open:
                self.xbee.close()
            self.connected = False
            self.export_btn.config(state=tk.NORMAL)
            self.refresh_btn.config(state=tk.NORMAL)
            self.connect_btn.config(text="Connect")
            self.status_label.config(text="Status: Disconnected", fg="red")
            print(f"Disconnected serial device on {self.port_var.get()}")
        else: #connect command
            self.connected = True
            self.connect_btn.config(text="Disconnect")
            self.status_label.config(text="Status: Connected", fg="green")
            self.export_btn.config(state=tk.DISABLED)
            self.refresh_btn.config(state=tk.DISABLED)
            #thread for receiving
            self.stop_event.clear()
            # Serial receiver thread
            self.serial_thread = threading.Thread(target=self.readSerial, name="serial-receiver", daemon=False)
            self.serial_thread.start()
            # Parse worker threads
            self.worker_threads = [threading.Thread(target=self.parsePacket, args=(i,), name=f"parser-{i}", daemon=True)
                for i in range(PROCESSORS)]
            for t in self.worker_threads:
                t.start()


if __name__ == "__main__":
    root = tk.Tk()
    app = HedgeGS(root)
    root.mainloop()