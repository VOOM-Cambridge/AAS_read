
#!/usr/bin/env python
import pyudev
import evdev
import asyncio
import paho.mqtt.client as mqtt
from datetime import datetime
import json
import time
import tomli
import zlib
import os

with open("config/config.toml", "rb") as f:
        toml_conf = tomli.load(f)

# Scanner details 
serialID = toml_conf['constants']['serialID'] 
locationID = toml_conf['constants']['location'] 
#'16c0:27db'
#"Printin_Lab"
#usbPort = '1.2:10'

port = 1883
broker = toml_conf['constants']['brokerIP']
topic = "AAS/QR_Code/" +locationID + "/"

client = mqtt.Client("rfid1")

# find devices connected and look for scanner needed
def findDevice():
    context = pyudev.Context()
    rfid_device = []
    #print(list(context.list_devices(subsystem = 'input', ID_BUS = 'usb')))
    for device in context.list_devices(subsystem = 'input', ID_BUS = 'usb'):
        ID = device.properties['ID_VENDOR_ID'] + ":" + device.properties['ID_MODEL_ID']
        #ID = device
        if ID == serialID and device.device_node != None:
            dev = device
        #rfid_device = evdev.InputDevice(device.device_node)
            if device.tags.__contains__('power-switch'):
                x = evdev.InputDevice(device.device_node)
                rfid_device.append(x)
                print("device found")
                print(device)
    return rfid_device


def mqtt_send(dataIn):
    mess = {}
    mess["location"] = locationID
    mess["ASS"] = dataIn
    mess["timestamp"]= str(datetime.now())
    mess_send = json.dumps(mess)
    print(mess)
    client.connect(broker, port)
    time.sleep(0.1)
    client.publish(topic, mess_send)

def findName(dataIn):
    dictData = json.loads(dataIn)
    try:
        return dictData["idShort"]
    except:
        return "unkown" + str(datetime.now())

def fileMake(dataIn):
    json_object = json.dumps(dataIn, indent=4)
    # Writing to sample.json
    script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
    name = findName(dataIn)
    rel_path = "/output/AAS/" + name.replace(".", "_") + ".json"
    rel_path = rel_path.replace(" ", "_")
    abs_file_path = script_dir + rel_path
    with open(abs_file_path, "w") as file:
        json.dump(dataIn, file)


async def helper(dev):
    barcode = ""
    async for ev in dev.async_read_loop():
        #keyname = x.keycode[4:]
        if ev.type == ecodes.EV_KEY:
            x=categorize(ev)
            
            if x.keystate == 1:
                #print(x)
                scancode = x.scancode
                keycode = x.keycode
                
                if keycode=="KEY_ENTER":
                    # finish entering data output now
                    print("data out")
                    print(barcode)
                    unzipData = zlib.decompress(barcode)
                    decodedData = unzipData.decode()
                    # update database infomation and send MQTT
                    print(decodedData)
                    mqtt_send(decodedData)
                    # make into file
                    fileMake(decodedData)
                    
                    # reset barcode input at the end
                    barcode = ""
                else:
                    barcode = barcode + keycode.split("_")[1]
                

while True:
    #print("start")
    
    rfid_device = findDevice()
    print(rfid_device)
    if len(rfid_device) > 0: 
        loop = asyncio.get_event_loop()
        loop.run_until_complete(helper(rfid_device[0]))
    else:
        print("no devices found")
