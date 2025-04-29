// Package vesc implements the subset of the VESC serial protocol the
// telemetry server uses (the pyvesc functionality from the Python version):
// framing with CRC16/XMODEM, COMM_GET_VALUES decoding, and the
// COMM_SET_DUTY / COMM_SET_CURRENT commands.
//
// Frame layout (short packets, payload < 256 bytes):
//
//	0x02 | payload length (1 byte) | payload | CRC16(payload) big-endian | 0x03
package vesc

import (
	"encoding/binary"
	"errors"
	"math"
)

// COMM packet ids (bldc firmware datatypes.h).
const (
	CommGetValues  = 4
	CommSetDuty    = 5
	CommSetCurrent = 6
)

const (
	startByte = 0x02
	endByte   = 0x03
)

// Crc16 computes CRC16/XMODEM (poly 0x1021, init 0) as used by the VESC firmware.
func Crc16(data []byte) uint16 {
	var crc uint16
	for _, b := range data {
		crc ^= uint16(b) << 8
		for i := 0; i < 8; i++ {
			if crc&0x8000 != 0 {
				crc = crc<<1 ^ 0x1021
			} else {
				crc <<= 1
			}
		}
	}
	return crc
}

// Encode wraps a payload into a VESC frame.
func Encode(payload []byte) []byte {
	frame := make([]byte, 0, len(payload)+5)
	frame = append(frame, startByte, byte(len(payload)))
	frame = append(frame, payload...)
	crc := Crc16(payload)
	frame = append(frame, byte(crc>>8), byte(crc), endByte)
	return frame
}

// EncodeSetDutyCycle builds a COMM_SET_DUTY frame. The duty value is scaled
// by 100000 (i.e. ±100000 = ±100%), matching pyvesc.SetDutyCycle usage in
// the Python server which pre-scales before encoding.
func EncodeSetDutyCycle(duty int32) []byte {
	payload := make([]byte, 5)
	payload[0] = CommSetDuty
	binary.BigEndian.PutUint32(payload[1:], uint32(duty))
	return Encode(payload)
}

// EncodeSetCurrent builds a COMM_SET_CURRENT frame. The current is in
// milliamps, matching pyvesc.SetCurrent usage in the Python server.
func EncodeSetCurrent(currentMilliamps int32) []byte {
	payload := make([]byte, 5)
	payload[0] = CommSetCurrent
	binary.BigEndian.PutUint32(payload[1:], uint32(currentMilliamps))
	return Encode(payload)
}

// EncodeGetValuesRequest builds the COMM_GET_VALUES poll request
// (pyvesc.encode_request(pyvesc.GetValues)).
func EncodeGetValuesRequest() []byte {
	return Encode([]byte{CommGetValues})
}

// Values is the decoded COMM_GET_VALUES response (FW 3.x field layout).
// Field names follow the modified pyvesc library the Python server used.
type Values struct {
	TempFetFiltered   float64 // °C
	TempMotorFiltered float64 // °C
	AvgMotorCurrent   float64 // A
	AvgInputCurrent   float64 // A
	AvgID             float64 // A
	AvgIQ             float64 // A
	DutyCycle         float64 // scaled /1000, 1.0 = full duty
	Rpm               float64 // electrical rpm
	VIn               float64 // V
	AmpHours          float64 // Ah
	AmpHoursCharged   float64 // Ah
	WattHours         float64 // Wh
	WattHoursCharged  float64 // Wh
	Tachometer        int32
	TachometerAbs     int32
	McFaultCode       uint8
}

// valuesPayloadLen = id(1) + 2*int16 + 4*int32 + int16 + int32 + int16 +
// 4*int32 + 2*int32 + fault(1).
const valuesPayloadLen = 1 + 2 + 2 + 4*4 + 2 + 4 + 2 + 4*4 + 4 + 4 + 1

// EncodeValues builds a COMM_GET_VALUES response frame (used by the device
// simulator and tests to play the role of a real VESC).
func EncodeValues(v Values) []byte {
	payload := make([]byte, 0, valuesPayloadLen)
	put16 := func(val float64, scale float64) {
		payload = binary.BigEndian.AppendUint16(payload, uint16(int16(math.Round(val*scale))))
	}
	put32 := func(val float64, scale float64) {
		payload = binary.BigEndian.AppendUint32(payload, uint32(int32(math.Round(val*scale))))
	}
	payload = append(payload, CommGetValues)
	put16(v.TempFetFiltered, 10)
	put16(v.TempMotorFiltered, 10)
	put32(v.AvgMotorCurrent, 100)
	put32(v.AvgInputCurrent, 100)
	put32(v.AvgID, 100)
	put32(v.AvgIQ, 100)
	put16(v.DutyCycle, 1000)
	put32(v.Rpm, 1)
	put16(v.VIn, 10)
	put32(v.AmpHours, 1e4)
	put32(v.AmpHoursCharged, 1e4)
	put32(v.WattHours, 1e4)
	put32(v.WattHoursCharged, 1e4)
	payload = binary.BigEndian.AppendUint32(payload, uint32(v.Tachometer))
	payload = binary.BigEndian.AppendUint32(payload, uint32(v.TachometerAbs))
	payload = append(payload, v.McFaultCode)
	return Encode(payload)
}

var (
	// ErrNoFrame means no complete valid frame was found in the buffer.
	ErrNoFrame = errors.New("vesc: no complete frame in buffer")
	// ErrNotValues means the frame decoded fine but wasn't a GET_VALUES response.
	ErrNotValues = errors.New("vesc: frame is not a COMM_GET_VALUES response")
)

// DecodeValues scans buf for a valid frame (tolerating leading/trailing
// garbage, like pyvesc.decode) and parses a COMM_GET_VALUES payload.
func DecodeValues(buf []byte) (*Values, error) {
	payload, err := decodeFrame(buf)
	if err != nil {
		return nil, err
	}
	if len(payload) < valuesPayloadLen || payload[0] != CommGetValues {
		return nil, ErrNotValues
	}
	v := &Values{}
	off := 1
	get16 := func(scale float64) float64 {
		raw := int16(binary.BigEndian.Uint16(payload[off:]))
		off += 2
		return float64(raw) / scale
	}
	get32 := func(scale float64) float64 {
		raw := int32(binary.BigEndian.Uint32(payload[off:]))
		off += 4
		return float64(raw) / scale
	}
	v.TempFetFiltered = get16(10)
	v.TempMotorFiltered = get16(10)
	v.AvgMotorCurrent = get32(100)
	v.AvgInputCurrent = get32(100)
	v.AvgID = get32(100)
	v.AvgIQ = get32(100)
	v.DutyCycle = get16(1000)
	v.Rpm = get32(1)
	v.VIn = get16(10)
	v.AmpHours = get32(1e4)
	v.AmpHoursCharged = get32(1e4)
	v.WattHours = get32(1e4)
	v.WattHoursCharged = get32(1e4)
	v.Tachometer = int32(binary.BigEndian.Uint32(payload[off:]))
	off += 4
	v.TachometerAbs = int32(binary.BigEndian.Uint32(payload[off:]))
	off += 4
	v.McFaultCode = payload[off]
	return v, nil
}

// decodeFrame finds and validates the first complete frame in buf,
// returning its payload.
func decodeFrame(buf []byte) ([]byte, error) {
	for start := 0; start < len(buf); start++ {
		if buf[start] != startByte {
			continue
		}
		if start+2 > len(buf) {
			break
		}
		payloadLen := int(buf[start+1])
		frameEnd := start + 2 + payloadLen + 3
		if frameEnd > len(buf) {
			continue
		}
		payload := buf[start+2 : start+2+payloadLen]
		crc := binary.BigEndian.Uint16(buf[start+2+payloadLen:])
		if crc == Crc16(payload) && buf[frameEnd-1] == endByte {
			return payload, nil
		}
	}
	return nil, ErrNoFrame
}
