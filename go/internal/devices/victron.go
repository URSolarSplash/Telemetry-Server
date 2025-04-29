package devices

import (
	"bytes"
	"fmt"
	"strconv"

	"telemetryserver/internal/data"
	"telemetryserver/internal/serialio"
)

// VictronDevice parses the Victron VE.Direct text protocol from a BMV battery
// monitor (port of VictronDevice2.py). Blocks of "label\tvalue\r\n" lines end
// with a Checksum line; the byte sum of a valid block is 0 mod 256.
type VictronDevice struct {
	*GenericSerialDevice
	statusVoltage       float64
	statusCurrent       float64
	statusPower         float64
	statusStateOfCharge int
	statusTimeRemaining int
	statusConsumedAh    float64
	blockBuffer         []byte
}

func NewVictronDevice(provider serialio.Provider, cache *data.DataCache, portName string) *VictronDevice {
	return &VictronDevice{
		GenericSerialDevice: NewGenericSerialDevice(provider, cache, portName, 19200),
	}
}

func (d *VictronDevice) Update() {
	if !d.open {
		return
	}
	// Read all available bytes
	if err := d.readAvailable(); err != nil {
		fmt.Println(err)
		d.Close()
		return
	}
	d.blockBuffer = append(d.blockBuffer, d.buffer...)
	d.buffer = nil

	// Process blocks in the buffer
	for {
		// Look for the Checksum line
		startIdx := bytes.Index(d.blockBuffer, []byte("\r\nChecksum\t"))
		if startIdx == -1 {
			break // No complete block yet
		}

		// Find the end of the Checksum line (ends with \r\n)
		endIdx := bytes.Index(d.blockBuffer[startIdx+2:], []byte("\r\n"))
		if endIdx == -1 {
			break // Incomplete Checksum line
		}
		endIdx += startIdx + 2 + 2 // Include the CR LF

		// Extract the block and remove it from the buffer
		block := d.blockBuffer[:endIdx]
		d.blockBuffer = d.blockBuffer[endIdx:]

		// Compute checksum
		total := 0
		for _, b := range block {
			total += int(b)
		}
		if total%256 != 0 {
			fmt.Println("Checksum error")
			continue
		}

		d.parseBlock(block)
	}
}

func (d *VictronDevice) parseBlock(block []byte) {
	lines := bytes.Split(block, []byte("\r\n"))
	tempData := make(map[string]string)
	for _, line := range lines {
		if len(line) == 0 {
			continue
		}
		parts := bytes.SplitN(line, []byte("\t"), 2)
		if len(parts) != 2 {
			continue // Invalid line
		}
		label := string(parts[0])
		// Skip Checksum processing as it's already validated
		if label == "Checksum" {
			continue
		}
		tempData[label] = string(parts[1])
	}
	d.updateVariables(tempData)
}

func (d *VictronDevice) updateVariables(dataMap map[string]string) {
	// Non-integer values (e.g. "---") abort the update, like the Python
	// ValueError handler.

	// Voltage (mV to V)
	if v, ok := dataMap["V"]; ok {
		mv, err := strconv.Atoi(v)
		if err != nil {
			return
		}
		d.statusVoltage = float64(mv) / 1000.0
		d.cache.Set("batteryVoltage", d.statusVoltage)
	}

	// Current (mA to A)
	if v, ok := dataMap["I"]; ok {
		ma, err := strconv.Atoi(v)
		if err != nil {
			return
		}
		d.statusCurrent = float64(ma) / 1000.0
		d.cache.Set("batteryCurrent", d.statusCurrent)
	}

	// Power (calculated as V * I)
	d.statusPower = d.statusVoltage * d.statusCurrent
	d.cache.Set("batteryPower", d.statusPower)

	// State of Charge (%)
	if v, ok := dataMap["SOC"]; ok {
		soc, err := strconv.Atoi(v)
		if err != nil {
			return
		}
		d.statusStateOfCharge = soc
		d.cache.Set("batteryStateOfCharge", float64(soc)/10)
	}

	// Time to Go (minutes)
	if v, ok := dataMap["TTG"]; ok {
		ttg, err := strconv.Atoi(v)
		if err != nil {
			return
		}
		d.statusTimeRemaining = ttg
		d.cache.Set("batteryTimeRemaining", float64(ttg))
	}

	// Consumed Amp Hours (mAh to Ah)
	if v, ok := dataMap["CE"]; ok {
		mah, err := strconv.Atoi(v)
		if err != nil {
			return
		}
		d.statusConsumedAh = float64(mah) / 1000.0
		d.cache.Set("batteryConsumedAh", d.statusConsumedAh)
	}
}
