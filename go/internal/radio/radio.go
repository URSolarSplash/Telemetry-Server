// Package radio ports server/radio.py: radio communication of telemetry data
// from the boat (Pi) to the shore computer. Receiving on the shore side is
// handled by devices.RadioDevice via the standard serial system.
//
// IN ORDER FOR RADIO TELEMETRY TO WORK CORRECTLY, BOTH DEVICES MUST HAVE THE
// SAME VERSION.
package radio

import (
	"fmt"

	"telemetryserver/internal/config"
	"telemetryserver/internal/data"
	"telemetryserver/internal/radioproto"
	"telemetryserver/internal/serialio"
	"telemetryserver/internal/stats"
)

// RadioManager handles output from the Pi to the shore computer.
type RadioManager struct {
	mode       int
	cache      *data.DataCache
	lastUpdate float64
	buffer     []byte
	port       serialio.Port
}

// NewRadioManager tries to open the fixed radio serial port
// (config.RadioSerialPort, /dev/serial0 on the Pi).
func NewRadioManager(cache *data.DataCache, provider serialio.Provider) *RadioManager {
	m := &RadioManager{
		cache:      cache,
		lastUpdate: data.Now(),
	}
	port, err := provider.Open(config.RadioSerialPort, 57600)
	if err != nil {
		m.mode = 0
		stats.SetHasRadio(false)
		fmt.Println("[Radio] No detected serial telemetry device.")
		return m
	}
	m.port = port
	m.mode = 1
	stats.SetHasRadio(true)
	fmt.Println("[Radio] Detected serial telemetry device.")
	return m
}

// Update reads control packets from the shore and periodically transmits all
// data points.
func (m *RadioManager) Update() {
	if m.mode != 1 {
		return
	}

	// Check for input packets; these are used for control signals from shore.
	if err := m.readIncoming(); err != nil {
		fmt.Println(err)
	}

	// Sends packets at a fixed rate
	if data.Now()-m.lastUpdate < config.RadioPacketRate {
		return
	}
	m.lastUpdate = data.Now()
	for _, key := range m.cache.GetKeys() {
		value, hasValue := m.cache.Get(key)
		m.write(key, value, hasValue)
	}
}

func (m *RadioManager) readIncoming() error {
	waiting, err := m.port.InWaiting()
	if err != nil {
		return err
	}
	if waiting > 0 {
		chunk := make([]byte, waiting)
		n, err := m.port.Read(chunk)
		if err != nil {
			return err
		}
		m.buffer = append(m.buffer, chunk[:n]...)
	}

	i := 0
	for i < len(m.buffer) && m.buffer[i] != radioproto.Header {
		i++
	}
	m.buffer = m.buffer[i:]

	if len(m.buffer) >= radioproto.PacketSize {
		packet := m.buffer[0:radioproto.PacketSize:radioproto.PacketSize]
		m.buffer = m.buffer[radioproto.PacketSize:]
		m.read(packet)
	}
	return nil
}

// write sends a data point update to the radio stream if radio is active.
func (m *RadioManager) write(dataName string, dataValue float64, hasValue bool) {
	if m.mode != 1 {
		return
	}
	dataID, ok := m.cache.KeyToIndex(dataName)
	if !ok {
		return
	}
	if _, err := m.port.Write(radioproto.Encode(dataID, dataValue, hasValue)); err != nil {
		fmt.Println(err)
	}
}

// read applies a control packet from the shore to the local cache.
func (m *RadioManager) read(packet []byte) {
	dataID, value, hasValue := radioproto.Decode(packet)
	dataKey, ok := m.cache.IndexToKey(dataID)
	if !ok || !hasValue {
		return
	}
	m.cache.Set(dataKey, value)
}

// Shutdown closes the radio port.
func (m *RadioManager) Shutdown() {
	if m.port != nil {
		m.port.Close()
	}
	fmt.Println("[Radio] shutdown complete.")
}
