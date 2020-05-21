#!/usr/bin/env python3
from bluepy.btle import UUID, Peripheral, ADDR_TYPE_PUBLIC, DefaultDelegate

BATTERY_HANDLE = 0x0018
TEMP_HUM_WRITE_HANDLE = 0x0010
TEMP_HUM_READ_HANDLE = 0x000E
TEMP_HUM_WRITE_VALUE = bytearray([0x01, 0x10])

class XiaomiMJHTDelegate(DefaultDelegate):
	def __init__ (self, parent):
		DefaultDelegate.__init__(self)

		self.__parent = parent

	def handleNotification (self, cHandle, data):
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

	def processData (self, data):
		'''The format of data is b"T=22.9 H=55.8\x00"'''
		temperature = data[2:6].decode('utf-8')
		humidity = data[9:13].decode('utf-8')

		self.__lastTemp = float(temperature)
		self.__lastHum = float(humidity)

	def readData (self):
		print("reading data from device " + self.__mac)

		p = Peripheral(self.__mac, iface=0)
		p.withDelegate(self.__delegate)

		try:
			battery = p.readCharacteristic(BATTERY_HANDLE)
			self.__lastBattery = battery[0]
		except:
			print("failed to read battery from " + self.__mac)

		p.writeCharacteristic(TEMP_HUM_WRITE_HANDLE, TEMP_HUM_WRITE_VALUE)
		if not p.waitForNotifications(3.0):
			print("failed to read data from " + self.__mac)

		print('Temperature is ' + str(self.__lastTemp))
		print('Humidity is ' + str(self.__lastHum))
		print('Battery is ' + str(self.__lastBattery))

		try:
			p.disconnect()
		except:
			pass

sensor = XiaomiMJHT(4, "58:2D:34:34:60:EC")
sensor.readData()
