package vesc

import (
	"bytes"
	"testing"
)

func TestCrc16KnownValue(t *testing.T) {
	// CRC16/XMODEM("123456789") = 0x31C3 (standard check value)
	if got := Crc16([]byte("123456789")); got != 0x31C3 {
		t.Fatalf("crc = %#x, want 0x31c3", got)
	}
}

func TestEncodeFrameLayout(t *testing.T) {
	frame := Encode([]byte{CommGetValues})
	want := []byte{0x02, 0x01, 0x04}
	if !bytes.Equal(frame[:3], want) {
		t.Fatalf("frame prefix = %v, want %v", frame[:3], want)
	}
	if frame[len(frame)-1] != 0x03 {
		t.Fatal("frame must end with 0x03")
	}
}

func TestSetDutyAndCurrentFrames(t *testing.T) {
	duty := EncodeSetDutyCycle(100000)
	if duty[2] != CommSetDuty {
		t.Fatalf("duty command id = %d", duty[2])
	}
	if got := int32(uint32(duty[3])<<24 | uint32(duty[4])<<16 | uint32(duty[5])<<8 | uint32(duty[6])); got != 100000 {
		t.Fatalf("duty payload = %d", got)
	}

	current := EncodeSetCurrent(-60000)
	if current[2] != CommSetCurrent {
		t.Fatalf("current command id = %d", current[2])
	}
	if got := int32(uint32(current[3])<<24 | uint32(current[4])<<16 | uint32(current[5])<<8 | uint32(current[6])); got != -60000 {
		t.Fatalf("current payload = %d", got)
	}
}

func TestValuesRoundtrip(t *testing.T) {
	in := Values{
		TempFetFiltered:   41.2,
		TempMotorFiltered: 55.7,
		AvgMotorCurrent:   -42.25,
		AvgInputCurrent:   -20.5,
		DutyCycle:         0.85,
		Rpm:               3120,
		VIn:               36.4,
		AmpHours:          1.25,
		McFaultCode:       2,
	}
	frame := EncodeValues(in)
	out, err := DecodeValues(frame)
	if err != nil {
		t.Fatal(err)
	}
	approx := func(name string, got, want float64) {
		t.Helper()
		if diff := got - want; diff > 1e-6 || diff < -1e-6 {
			t.Fatalf("%s = %v, want %v", name, got, want)
		}
	}
	approx("TempFetFiltered", out.TempFetFiltered, 41.2)
	approx("TempMotorFiltered", out.TempMotorFiltered, 55.7)
	approx("AvgMotorCurrent", out.AvgMotorCurrent, -42.25)
	approx("AvgInputCurrent", out.AvgInputCurrent, -20.5)
	approx("DutyCycle", out.DutyCycle, 0.85)
	approx("Rpm", out.Rpm, 3120)
	approx("VIn", out.VIn, 36.4)
	approx("AmpHours", out.AmpHours, 1.25)
	if out.McFaultCode != 2 {
		t.Fatalf("fault = %d", out.McFaultCode)
	}
}

func TestDecodeToleratesGarbage(t *testing.T) {
	frame := EncodeValues(Values{Rpm: 1234})
	buf := append([]byte{0xDE, 0xAD, 0x02, 0xBE}, frame...)
	buf = append(buf, 0xEF, 0x00)
	out, err := DecodeValues(buf)
	if err != nil {
		t.Fatal(err)
	}
	if out.Rpm != 1234 {
		t.Fatalf("rpm = %v", out.Rpm)
	}
}

func TestDecodeRejectsCorruptFrame(t *testing.T) {
	frame := EncodeValues(Values{Rpm: 1234})
	frame[10] ^= 0xFF // corrupt payload -> CRC mismatch
	if _, err := DecodeValues(frame); err == nil {
		t.Fatal("corrupt frame must not decode")
	}
	if _, err := DecodeValues([]byte{1, 2, 3}); err == nil {
		t.Fatal("junk must not decode")
	}
	if _, err := DecodeValues(Encode([]byte{CommSetDuty, 0, 0, 0, 0})); err != ErrNotValues {
		t.Fatal("non-GetValues frame must return ErrNotValues")
	}
}
