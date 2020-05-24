#!/usr/bin/env python3

import sys
import json
import logging
import threading
import paho.mqtt.client as mqtt

from bluepy.btle import UUID, Peripheral, ADDR_TYPE_PUBLIC, DefaultDelegate

BROKER_ADDRESS = '127.0.0.1'
DEFAULT_IN_TOPIC = 'domoticz/in'
DEFAULT_OUT_TOPIC = 'domoticz/out'
HCI_INTERFACE = 0

''' Each device has to have two methods readData() and processCommand() '''

''' Lotus Lantern LED Stripe'''
WRITE_HANDLE = 0x0008

class LotusLanternLEDStripe:
	def __init__ (self, id, mac):
		self.__id = id
		self.__mac = mac

	def idx (self):
		return self.__id

	def readData (self, mqttClient):
		pass

	def processCommand (self, cmd):
		print("LED stripe " + self.__mac + " is processing command")
		sys.stdout.flush()

		self.changeState(cmd['nvalue'])

	def changeState (self, onOff):
		print("LED stripe " + self.__mac + " is changing state to " + str(onOff))
		sys.stdout.flush()

		p = Peripheral(self.__mac, iface=HCI_INTERFACE)
		if (onOff == 0):
			data = bytearray([0x7e, 0x04, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef])
		else:
			data = bytearray([0x7e, 0x04, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef])

		try:
			p.writeCharacteristic(WRITE_HANDLE, data)
		except:
			print("failed to change state of lotus lantern " + self.__mac)
			sys.stdout.flush()

		try:
			p.disconnect()
		except:
			pass

''' Xiaomi MJH '''
BATTERY_HANDLE = 0x0018
TEMP_HUM_WRITE_HANDLE = 0x0010
TEMP_HUM_READ_HANDLE = 0x000E
TEMP_HUM_WRITE_VALUE = bytearray([0x01, 0x10])

class XiaomiMJHTDelegate(DefaultDelegate):
	def __init__ (self, parent):
		DefaultDelegate.__init__(self)

		self.__parent = parent

	def handleNotification (self, cHandle, data):
		print("handeling notification from " + self.__parent.mac())
		sys.stdout.flush()

		if (cHandle == TEMP_HUM_READ_HANDLE):
			self.__parent.processData(data)

class XiaomiMJHT:
	def __init__ (self, id, mac):
		self.__id = id
		self.__mac = mac

		self.__delegate = XiaomiMJHTDelegate(self)

		self.__lastBattery = None
		self.__lastTemp = None
		self.__LastHum = None

	def idx (self):
                return self.__id

	def mac (self):
		return self.__mac

	def processCommand (self, cmd):
		pass

	def processData (self, data):
		'''The format of data is b"T=22.9 H=55.8\x00"'''
		temperature = data[2:6].decode('utf-8')
		humidity = data[9:13].decode('utf-8')

		self.__lastTemp = float(temperature)
		self.__lastHum = float(humidity)

	def readData (self, mqttClient):
		print("reading data from device " + self.__mac)
		sys.stdout.flush()

		p = Peripheral(self.__mac, iface=HCI_INTERFACE)
		p.withDelegate(self.__delegate)

		try:
			battery = p.readCharacteristic(BATTERY_HANDLE)
			self.__lastBattery = battery[0]
		except:
			print("failed to read battery from " + self.__mac)
			sys.stdout.flush()

		p.writeCharacteristic(TEMP_HUM_WRITE_HANDLE, TEMP_HUM_WRITE_VALUE)
		if not p.waitForNotifications(3.0):
			print("failed to read data from " + self.__mac)
			sys.stdout.flush()

		try:
			p.disconnect()
		except:
			pass

		print("read data from " + self.__mac + " " + str(self.__lastTemp) + "," + str(self.__lastHum) + "," + str(self.__lastBattery))
		sys.stdout.flush()

		msg =\
		'{'\
			'"idx" : ' + str(self.__id) + ','\
			'"nvalue" : 0,'\
			'"svalue" : "' + str(self.__lastTemp) + ';' + str(self.__lastHum) + ';0",'\
			'"Battery" : ' + str(self.__lastBattery) + ' '\
		'}'
		mqttClient.publish(DEFAULT_IN_TOPIC, msg);

''' Core of BLE module '''
class BLEModule:
	def __init__ (self):
		self.__devices = {}
		self.__sleepTimeout = 120.0
		self.__stop = False
		self.__stopEvent = threading.Event()
		self.__mqttClient = mqtt.Client("PythonIoT", userdata={'bleModule':self})
		self.__mqttClient.on_message = self.onMessage

	def run (self):
		print("starting the BLE module")
		sys.stdout.flush()

		self.__mqttClient.connect(BROKER_ADDRESS)
		self.__mqttClient.subscribe(DEFAULT_OUT_TOPIC, 0)
		self.__mqttClient.loop_start()

		while (not self.__stop):
			for mac in self.__devices:
				try:
					self.__devices[mac].readData(self.__mqttClient)
				except Exception as ex:
					print("reading from device " + mac + " failed (" + str(ex) + ")")
					sys.stdout.flush()

			self.__stopEvent.wait(self.__sleepTimeout)

		self.__mqttClient.loop_stop()
		self.__mqttClient.disconnect()

		print("stopping the BLE module")
		sys.stdout.flush()

		self.__stopEvent.clear()
		self.__stop = False

	def stop (self):
		self.__stop = True
		self.__stopEvent.set()

	def onMessage (self, mqttc, userdata, msg):
		data = json.loads(msg.payload.decode('utf-8'))

		print('received message from ' + msg.topic + ' for device with idx ' + str(data['idx']))
		sys.stdout.flush()

		try:
			for mac in userdata['bleModule'].__devices:
				device = userdata['bleModule'].__devices[mac]
				if device.idx() == data['idx']:
					try:
						device.processCommand(data)
					except:
						print("processing of message for device " + mac + " failed")
						sys.stdout.flush()
		except Exception as e:
			print(e)

	def registerXioamiMJHT (self, id, mac):
		print("registring the device " + mac)
		sys.stdout.flush()

		sensor = XiaomiMJHT(id, mac)
		self.__devices[mac] = sensor

	def registerLLLEDStripe (self, id, mac):
		print("registring the device " + mac)
		sys.stdout.flush()

		stripe = LotusLanternLEDStripe(id, mac)
		self.__devices[mac] = stripe


if __name__ == "__main__":
	bleModule = BLEModule()
	bleModuleThread = threading.Thread(target = bleModule.run)

	event = threading.Event()

	try:
		bleModuleThread.start()
		bleModule.registerXioamiMJHT(4, "58:2D:34:34:60:EC") # upper bathroom
		bleModule.registerXioamiMJHT(5, "58:2D:34:34:5F:77") # upper bedroom
		bleModule.registerXioamiMJHT(7, "58:2D:34:3A:82:58") # lower bedroom
		bleModule.registerXioamiMJHT(8, "58:2D:34:3A:82:D9") # living room
		bleModule.registerLLLEDStripe(6, "BE:FF:10:00:1E:E7") # David's room
		event.wait()
	except KeyboardInterrupt:
		bleModule.stop()

	bleModuleThread.join()
