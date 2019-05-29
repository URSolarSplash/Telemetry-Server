import pyvesc
import serial
import time

conn=serial.Serial(port="/dev/ttyACM0",baudrate=115200)

#request data
conn.write(pyvesc.encode_request(pyvesc.GetValues))

while conn.inWaiting() < 70:
	pass

_buffer= conn.read(70)
(vescMessage,consumed) = pyvesc.decode(_buffer)

if(vescMessage):
	print("VESC Data:")
	print(vescMessage.temp_fet_filtered)
	print(vescMessage.temp_motor_filtered)
	print(vescMessage.avg_motor_current)
	print(vescMessage.avg_input_current)
	print(vescMessage.duty_cycle)
	print(vescMessage.rpm)
	print(vescMessage.v_in)
	print(vescMessage.amp_hours)
	print(vescMessage.watt_hours)
	print(vescMessage.tachometer)
	print(vescMessage.tachometer_abs)
	print(vescMessage.mc_fault_code)
	print(vescMessage.temp_mos1)
	print(vescMessage.temp_mos2)
	print(vescMessage.temp_mos3)

throt_msg = pyvesc.SetDutyCycle(10000)
conn.write(pyvesc.encode(throt_msg))
