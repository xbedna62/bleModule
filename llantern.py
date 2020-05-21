#!/usr/bin/env python3
from bluepy.btle import UUID, Peripheral, ADDR_TYPE_PUBLIC, DefaultDelegate
import paho.mqtt.client as mqtt
import json

WRITE_HANDLE = 0x0008

class LotusLanternLEDStripe:
	def __init__ (self, id, mac):
		self.__id = id
		self.__mac = mac

	def processCommand(self, cmd):
		print("LED stripe " + self.__mac + " is processing command!")

		if (cmd['nvalue'] == 0):
			self.switchOff()
		else:
			self.switchOn()

	def switchOn(self):
		print("LED stripe " + self.__mac + " is switching on")

		p = Peripheral(self.__mac, iface=0)

		data = bytearray([0x7e, 0x04, 0x04, 0xf0, 0x00, 0x01, 0xff, 0x00, 0xef])
		try:
			p.writeCharacteristic(WRITE_HANDLE, data)
		except:
			print("failed to write command SwitchOn to " + self.__mac)

		try:
			p.disconnect()
		except:
			pass

	def switchOff(self):
		print("LED stripe " + self.__mac + " is switching off")

		p = Peripheral(self.__mac, iface=0)

		data = bytearray([0x7e, 0x04, 0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0xef])
		try:
			p.writeCharacteristic(WRITE_HANDLE, data)
		except:
			print("failed to write command SwitchOff to " + self.__mac)

		try:
			p.disconnect()
		except:
			pass

def on_message(mqttc, obj, msg):
	print(msg.topic + " " + str(msg.qos) + " " + msg.payload.decode('utf-8'))

	try:
		data = json.loads(msg.payload.decode('utf-8'))
		print("index of device is " + str(data['idx']))
		if (data['idx'] == 6):
			stripe.processCommand(data)
	except Exception as e:
		print(e)


def on_subscribe(mqttc, obj, mid, granted_qos):
	print("subscribed: " + str(mid) + " " + str(granted_qos))

stripe = LotusLanternLEDStripe(6, "BE:FF:10:00:1E:E7")

mqttc = mqtt.Client()
mqttc.on_message = on_message
mqttc.on_subscribe = on_subscribe
mqttc.connect("192.168.101.254", 1883, 60)
mqttc.subscribe('domoticz/out', 0)

mqttc.loop_forever()
