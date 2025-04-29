package devices

import (
	"encoding/binary"
	"fmt"
	"math"

	"telemetryserver/internal/data"
	"telemetryserver/internal/serialio"
	"telemetryserver/internal/stats"
)

// StatelessTelemetryNodeDevice implements the stateless telemetry node
// protocol (port of StatelessTelemetryNodeDevice.py). Nodes send encoded
// packets periodically; each valid packet may be answered with a response.
//
// Packet breakdown (16 bytes):
//   - Byte 0:     Header (0xF0)
//   - Byte 1-4:   Data (1)
//   - Byte 5-8:   Data (2)
//   - Byte 9-12:  Data (3)
//   - Byte 13:    Data (misc)
//   - Byte 14:    Packet metadata (Device ID and Packet Number)
//   - Byte 15:    8-bit Checksum

// Device ID constants.
const (
	DeviceAlltrax      = 0x00
	DeviceVesc         = 0x01
	DeviceMotorBoard   = 0x02
	DeviceBatteryBoard = 0x03
	DeviceGpsImu       = 0x04
	DeviceThrottle     = 0x05
	DeviceSolar        = 0x06
)

const nodePacketHeader = 0xF0

// KnotsToMph converts GPS speed over ground.
const KnotsToMph = 1.15078

type StatelessTelemetryNodeDevice struct {
	*GenericSerialDevice
}

func NewStatelessTelemetryNodeDevice(provider serialio.Provider, cache *data.DataCache, portName string) *StatelessTelemetryNodeDevice {
	return &StatelessTelemetryNodeDevice{
		GenericSerialDevice: NewGenericSerialDevice(provider, cache, portName, 115200),
	}
}

// float32LE decodes the reversed-byte-order floats the nodes send
// (Python: struct.unpack(">f", bytes([b[4],b[3],b[2],b[1]]))).
func float32LE(b []byte) float64 {
	return float64(math.Float32frombits(binary.LittleEndian.Uint32(b)))
}

func (d *StatelessTelemetryNodeDevice) handlePacket(packet []byte) {
	deviceID := (packet[14] & 0xF0) >> 4
	packetNum := packet[14] & 0x0F

	switch deviceID {
	case DeviceAlltrax:
		d.cache.Set("boatConfig", 1)
	case DeviceBatteryBoard:
		// no data currently
	case DeviceMotorBoard:
		motorTemp := float32LE(packet[1:5])
		motorRpm := float64(binary.LittleEndian.Uint32(packet[5:9]))
		propRpm := float64(binary.LittleEndian.Uint32(packet[9:13]))
		if d.cache.GetNumerical("boatConfig", 0) == 1 {
			d.cache.Set("motorTemp", motorTemp)
		}
		d.cache.Set("motorRpm", motorRpm)
		d.cache.Set("propRpm", propRpm)
	case DeviceGpsImu:
		switch packetNum {
		case 0:
			imuPitch := float32LE(packet[1:5])
			imuRoll := float32LE(packet[5:9])
			gpsFix := packet[9]
			gpsNumSatellites := packet[10]
			gpsHeading := (float64(packet[11]) / 255.0) * 360.0
			d.cache.Set("imuPitch", imuPitch)
			d.cache.Set("imuRoll", imuRoll)
			d.cache.Set("gpsFix", float64(gpsFix))
			// Only save GPS data points if we have a GPS fix.
			if gpsFix != 0 {
				d.cache.Set("gpsNumSatellites", float64(gpsNumSatellites))
				d.cache.Set("gpsHeading", gpsHeading)
			}
		case 1:
			latitude := float32LE(packet[1:5])
			longitude := float32LE(packet[5:9])
			speedKnots := float32LE(packet[9:13])
			gpsFix := packet[13]
			d.cache.Set("gpsFix", float64(gpsFix))
			// Only save GPS data points if we have a GPS fix.
			if gpsFix != 0 {
				d.cache.Set("gpsLatitude", latitude)
				d.cache.Set("gpsLongitude", longitude)
				d.cache.Set("gpsSpeedKnots", speedKnots)
				d.cache.Set("gpsSpeedMph", speedKnots*KnotsToMph)
			}
		}
	case DeviceThrottle:
		throttleValue := float64(uint16(packet[2])<<8 | uint16(packet[1]))
		throttleEnabled := float64(packet[3])
		throttleMode := float64(packet[4])
		// boat config is now determined by having either VESC or Alltrax attached
		d.cache.Set("throttleInput", throttleValue)
		d.cache.Set("throttleEnabled", throttleEnabled)
		d.cache.Set("throttleMode", throttleMode)
	case DeviceSolar:
		outCurrent1 := float32LE(packet[1:5])
		outCurrent2 := float32LE(packet[5:9])
		totalCurrent := float32LE(packet[9:13])
		d.cache.Set("solarChargerCurrent1", outCurrent1)
		d.cache.Set("solarChargerCurrent2", outCurrent2)
		d.cache.Set("solarChargerCurrentTotal", totalCurrent)
	}
}

// sendResponse sends a response packet to a device, providing the
// opportunity to feed back data to the nodes.
func (d *StatelessTelemetryNodeDevice) sendResponse(deviceID byte) {
	packet := make([]byte, 16)
	packet[0] = nodePacketHeader

	switch deviceID {
	case DeviceAlltrax:
		// Write back the value of the throttle for the motor controller output.
		// Only write a value when we are in sprint mode.
		throttle := 0
		if d.cache.GetNumerical("boatConfig", 0) == 1 {
			throttle = int(d.cache.GetNumerical("throttle", 0))
		}
		packet[1] = byte(throttle & 0xFF)
		packet[2] = byte((throttle & 0xFF00) >> 8)
		packet[3] = byte(int(d.cache.GetNumerical("throttleEnabled", 0)))
	default:
		return
	}

	// Generate checksum at the end of the packet, and write it out.
	packet[15] = EncodeChecksum(packet)
	if _, err := d.port.Write(packet); err != nil {
		fmt.Println("Serial error:", err)
	}
}

// Update handles reading data, parsing, and response packets.
func (d *StatelessTelemetryNodeDevice) Update() {
	if err := d.readAvailable(); err != nil {
		fmt.Println("[Stateless Telemetry Node] Error: " + err.Error())
		d.Close()
		return
	}

	// After this, the first byte is guaranteed to be a header, or empty.
	d.discardToHeader(nodePacketHeader)

	// If the buffer has a full packet, consume and read it.
	if len(d.buffer) >= 16 {
		packet := d.buffer[0:16:16]
		deviceID := (packet[14] & 0xF0) >> 4
		d.buffer = d.buffer[16:]

		// Validate the checksum
		if DecodeChecksum(packet) == 255 {
			d.handlePacket(packet)
			d.sendResponse(deviceID) // Send a response after reading a valid packet.
		} else {
			fmt.Println("[Telemetry Node] Packet dropped!")
			stats.IncDroppedNodePackets()
		}
	}
}

// EncodeChecksum computes the trailing checksum byte over the first 15 bytes.
func EncodeChecksum(packet []byte) byte {
	sum := 0
	for i := 0; i < 15; i++ {
		sum += int(packet[i])
	}
	return byte(255 - (sum % 256))
}

// DecodeChecksum sums all 16 bytes; a valid packet yields 255.
func DecodeChecksum(packet []byte) int {
	sum := 0
	for i := 0; i < 16; i++ {
		sum += int(packet[i])
	}
	return sum % 256
}
