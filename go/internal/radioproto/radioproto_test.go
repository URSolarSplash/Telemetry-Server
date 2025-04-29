package radioproto

import "testing"

func TestRoundtrip(t *testing.T) {
	packet := Encode(17, 36.5, true)
	if len(packet) != PacketSize {
		t.Fatalf("packet size = %d", len(packet))
	}
	if packet[0] != Header {
		t.Fatal("missing header")
	}
	id, value, ok := Decode(packet)
	if !ok || id != 17 || value != 36.5 {
		t.Fatalf("decode = (%d, %v, %v)", id, value, ok)
	}
}

func TestNoValueEncodesAsNaN(t *testing.T) {
	packet := Encode(3, 0, false)
	id, _, ok := Decode(packet)
	if ok {
		t.Fatal("NaN payload must decode as no-value")
	}
	if id != 3 {
		t.Fatalf("id = %d", id)
	}
}

func TestDecodeWrongSize(t *testing.T) {
	if _, _, ok := Decode([]byte{Header, 1, 2}); ok {
		t.Fatal("short packet must not decode")
	}
}
