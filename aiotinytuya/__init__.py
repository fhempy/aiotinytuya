# TinyTuya Module
# -*- coding: utf-8 -*-
"""
 Python module to interface with Tuya WiFi smart devices

 Author: Jason A. Cox
 For more information see https://github.com/jasonacox/tinytuya

  Local Control Classes
    OutletDevice(dev_id, address=None, local_key=None, dev_type='default', connection_timeout=5, version=3.1, persist=False)
    CoverDevice(...)
    BulbDevice(...)
    Device(...)
        dev_id (str): Device ID e.g. 01234567891234567890
        address (str, optional): Device Network IP Address e.g. 10.0.1.99, or None to try and find the device
        local_key (str, optional): The encryption key. Defaults to None. If None, key will be looked up in DEVICEFILE if available
        dev_type (str, optional): Device type for payload options (see below)
        connection_timeout (float, optional): The default socket connect and data timeout
        version (float, optional): The API version to use. Defaults to 3.1
        persist (bool, optional): Make a persistant connection to the device
    Cloud(apiRegion, apiKey, apiSecret, apiDeviceID, new_sign_algorithm)

  Functions
    Device(XenonDevice)
        json = status()                    # returns json payload
        set_version(version)               # 3.1 [default] or 3.3
        set_socketPersistent(False/True)   # False [default] or True
        set_socketNODELAY(False/True)      # False or True [default]
        set_socketRetryLimit(integer)      # retry count limit [default 5]
        set_socketTimeout(timeout)         # set connection timeout in seconds [default 5]
        set_dpsUsed(dps_to_request)        # add data points (DPS) to request
        add_dps_to_request(index)          # add data point (DPS) index set to None
        set_retry(retry=True)              # retry if response payload is truncated
        set_status(on, switch=1, nowait)   # Set status of switch to 'on' or 'off' (bool)
        set_value(index, value, nowait)    # Set int value of any index.
        heartbeat(nowait)                  # Send heartbeat to device
        updatedps(index=[1], nowait)       # Send updatedps command to device
        turn_on(switch=1, nowait)          # Turn on device / switch #
        turn_off(switch=1, nowait)         # Turn off
        set_timer(num_secs, nowait)        # Set timer for num_secs
        set_debug(toggle, color)           # Activate verbose debugging output
        set_sendWait(num_secs)             # Time to wait after sending commands before pulling response
        detect_available_dps()             # Return list of DPS available from device
        generate_payload(command, data)    # Generate TuyaMessage payload for command with data
        send(payload)                      # Send payload to device (do not wait for response)
        receive()                          # Receive payload from device

    OutletDevice:
        set_dimmer(percentage):

    CoverDevice:
        open_cover(switch=1):
        close_cover(switch=1):
        stop_cover(switch=1):

    BulbDevice
        set_colour(r, g, b, nowait):
        set_hsv(h, s, v, nowait):
        set_white(brightness, colourtemp, nowait):
        set_white_percentage(brightness=100, colourtemp=0, nowait):
        set_brightness(brightness, nowait):
        set_brightness_percentage(brightness=100, nowait):
        set_colourtemp(colourtemp, nowait):
        set_colourtemp_percentage(colourtemp=100, nowait):
        set_scene(scene, nowait):             # 1=nature, 3=rave, 4=rainbow
        set_mode(mode='white', nowait):       # white, colour, scene, music
        result = brightness():
        result = colourtemp():
        (r, g, b) = colour_rgb():
        (h,s,v) = colour_hsv()
        result = state():

    Cloud
        setregion(apiRegion)
        getdevices(verbose=False)
        getstatus(deviceid)
        getfunctions(deviceid)
        getproperties(deviceid)
        getdps(deviceid)
        sendcommand(deviceid, commands)

 Credits
  * TuyaAPI https://github.com/codetheweb/tuyapi by codetheweb and blackrozes
    For protocol reverse engineering
  * PyTuya https://github.com/clach04/python-tuya by clach04
    The origin of this python module (now abandoned)
  * LocalTuya https://github.com/rospogrigio/localtuya-homeassistant by rospogrigio
    Updated pytuya to support devices with Device IDs of 22 characters

"""

import asyncio

from .BulbDevice import BulbDevice
from .Cloud import Cloud
from .core import *
from .core import __author__, __version__
from .CoverDevice import CoverDevice
from .OutletDevice import OutletDevice


class HAInterface:
    def __init__(self, device, protocol_version):
        self.dps_cache = {}
        self.device = device
        self.protocol_version = protocol_version
        self.isstillalive = True

    def isalive(self):
        return self.isstillalive

    async def close(self):
        self.device.device.close()
        self.isstillalive = False

    async def set_dp(self, state, dp_index):
        await self.device.device.set_status(state, dp_index)

    async def detect_available_dps(self):
        while not self.device.started:
            await asyncio.sleep(1)

        return self.dps_cache


class DeviceWrapper:
    heartbeatssend = 0
    heartbeatsreceived = 0

    def __init__(self, device, listener):
        self.dps_cache = {}
        self.device = device
        self.listener = listener
        self.started = False


async def heartbeat(device, haobj):
    devid = device.device.get_deviceid()
    await asyncio.sleep(5)
    log.debug("[" + devid + "] start heartbeat thread")
    await device.device.start_socket()
    while haobj.isalive():
        if device.device.get_version() == 3.4:
            await device.device.updatedps()
            await asyncio.sleep(2)
            device.started = True
        else:
            await device.device.heartbeat(nowait=True)
            device.started = True
        device.heartbeatssend = device.heartbeatssend + 1
        if device.device.get_version() == 3.4:
            await asyncio.sleep(5)
        else:
            await asyncio.sleep(10)


async def main(device, haobj):
    devid = device.device.get_deviceid()
    log.debug("[" + devid + "] start main thread")

    await device.device.start_socket()
    await device.device.status_quick()

    while haobj.isalive():
        try:
            data = await device.device.getdata()
        except Exception:
            if device.listener != None:
                device.listener.disconnected()
            await haobj.close()

        if data != None:
            log.debug("[" + devid + "] Got data: " + str(data))
            if "Error" in data:
                log.debug("[" + devid + "] Received error response")

            elif type(data) == TuyaMessage:
                if data.cmd == 9:
                    log.debug("[" + devid + "] Received Heartbeat response")
                    device.heartbeatsreceived = device.heartbeatsreceived + 1
                    if device.listener != None:
                        device.listener.status_updated({})

                if data.cmd == 7:
                    log.debug("[" + devid + "] Received SET_DP response")
            else:
                if "dps" in data:
                    haobj.dps_cache.update(data["dps"])

                if device.listener != None:
                    device.listener.status_updated(data)


async def connect(
    address,
    device_id,
    local_key,
    protocol_version,
    listener=None,
):

    device = OutletDevice(device_id, address, local_key, version=protocol_version)
    device.set_socketPersistent(True)
   
    # start_socket here to generate exception on error
    await device.start_socket()

    dev = DeviceWrapper(device, listener)
    haobj = HAInterface(dev, protocol_version)

    task1 = asyncio.create_task(main(dev, haobj))
    task2 = asyncio.create_task(heartbeat(dev, haobj))

    return haobj
