// Package radioproto implements the 6-byte radio telemetry packet shared by
// the RadioManager (boat side) and RadioDevice (shore side).
//
// Each packet consists of six bytes:
//
//	byte 1:     packet header (0xF0)
//	byte 2:     data point ID
//	byte 3 - 6: data (big-endian float32; NaN represents "no value")
package radioproto

import (
	"encoding/binary"
	"math"
)

// Header is the packet start byte.
const Header = 0xF0

// PacketSize is the fixed radio packet length.
const PacketSize = 6

// Encode builds a packet for a data point. hasValue=false encodes NaN,
// representing None for the data point.
func Encode(dataID int, value float64, hasValue bool) []byte {
	packet := make([]byte, PacketSize)
	packet[0] = Header
	packet[1] = byte(dataID)
	f := float32(math.NaN())
	if hasValue {
		f = float32(value)
	}
	binary.BigEndian.PutUint32(packet[2:6], math.Float32bits(f))
	return packet
}

// Decode parses a packet into its data point ID and value. hasValue=false
// means the payload was NaN (no value).
func Decode(packet []byte) (dataID int, value float64, hasValue bool) {
	if len(packet) != PacketSize {
		return 0, 0, false
	}
	dataID = int(packet[1])
	f := math.Float32frombits(binary.BigEndian.Uint32(packet[2:6]))
	if math.IsNaN(float64(f)) {
		return dataID, 0, false
	}
	return dataID, float64(f), true
}
