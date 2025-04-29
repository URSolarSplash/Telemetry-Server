package devices

import (
	"testing"

	"telemetryserver/internal/config"
	"telemetryserver/internal/data"
	"telemetryserver/internal/serialio"
	"telemetryserver/internal/stats"
)

// buildVEDirectBlock renders "label\tvalue" lines in the VE.Direct framing
// the parser expects and appends a Checksum line whose byte makes the whole
// block sum to 0 mod 256 (as validated by VictronDevice2.py's algorithm).
func buildVEDirectBlock(t *testing.T, fields [][2]string) []byte {
	t.Helper()
	var block []byte
	for _, f := range fields {
		block = append(block, []byte("\r\n"+f[0]+"\t"+f[1])...)
	}
	block = append(block, []byte("\r\nChecksum\t")...)
	// The parser's block includes the CRLF that terminates the checksum line.
	sum := 0
	for _, b := range block {
		sum += int(b)
	}
	sum += int('\r') + int('\n')
	check := byte((256 - sum%256) % 256)
	if check == '\r' || check == '\n' {
		t.Fatal("test data produces a CR/LF checksum byte; adjust field values")
	}
	block = append(block, check, '\r', '\n')
	return block
}

func newVictronUnderTest(t *testing.T) (*VictronDevice, *serialio.FakePort, *data.DataCache) {
	t.Helper()
	stats.Reset()
	provider := serialio.NewFakeProvider()
	port := provider.Plug("/dev/ttyUSB3", "VE Direct cable")
	cache := data.NewDataCache(config.DataKeys)
	dev := NewVictronDevice(provider, cache, "/dev/ttyUSB3")
	return dev, port, cache
}

func TestVictronParsesBlock(t *testing.T) {
	dev, port, cache := newVictronUnderTest(t)
	block := buildVEDirectBlock(t, [][2]string{
		{"V", "36500"},  // 36.5 V
		{"I", "-15250"}, // -15.25 A
		{"SOC", "855"},  // 85.5 %
		{"TTG", "120"},  // 120 min
		{"CE", "-5750"}, // -5.75 Ah
	})
	port.FeedToServer(block)
	dev.Update()

	if v := cache.GetNumerical("batteryVoltage", -1); v != 36.5 {
		t.Fatalf("batteryVoltage = %v", v)
	}
	if v := cache.GetNumerical("batteryCurrent", 0); v != -15.25 {
		t.Fatalf("batteryCurrent = %v", v)
	}
	if v := cache.GetNumerical("batteryPower", 0); v != 36.5*-15.25 {
		t.Fatalf("batteryPower = %v", v)
	}
	if v := cache.GetNumerical("batteryStateOfCharge", -1); v != 85.5 {
		t.Fatalf("batteryStateOfCharge = %v", v)
	}
	if v := cache.GetNumerical("batteryTimeRemaining", -1); v != 120 {
		t.Fatalf("batteryTimeRemaining = %v", v)
	}
	if v := cache.GetNumerical("batteryConsumedAh", 1); v != -5.75 {
		t.Fatalf("batteryConsumedAh = %v", v)
	}
}

func TestVictronBadChecksumIgnored(t *testing.T) {
	dev, port, cache := newVictronUnderTest(t)
	block := buildVEDirectBlock(t, [][2]string{{"V", "36500"}})
	block[3] ^= 0x01 // corrupt a data byte
	port.FeedToServer(block)
	dev.Update()

	if _, ok := cache.Get("batteryVoltage"); ok {
		t.Fatal("bad-checksum block must not update the cache")
	}
}

func TestVictronHandlesSplitReads(t *testing.T) {
	dev, port, cache := newVictronUnderTest(t)
	block := buildVEDirectBlock(t, [][2]string{{"V", "36500"}, {"I", "1000"}})

	// Deliver the block a few bytes at a time across updates.
	for i := 0; i < len(block); i += 5 {
		end := i + 5
		if end > len(block) {
			end = len(block)
		}
		port.FeedToServer(block[i:end])
		dev.Update()
	}

	if v := cache.GetNumerical("batteryVoltage", -1); v != 36.5 {
		t.Fatalf("batteryVoltage = %v after split reads", v)
	}
	if v := cache.GetNumerical("batteryCurrent", -1); v != 1 {
		t.Fatalf("batteryCurrent = %v after split reads", v)
	}
}

func TestVictronNonIntegerValuesSkipped(t *testing.T) {
	dev, port, cache := newVictronUnderTest(t)
	block := buildVEDirectBlock(t, [][2]string{{"V", "---"}})
	port.FeedToServer(block)
	dev.Update()
	if _, ok := cache.Get("batteryVoltage"); ok {
		t.Fatal("non-integer value must be skipped")
	}
}
