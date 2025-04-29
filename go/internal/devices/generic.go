// Package devices ports server/devices/: the serial device drivers that parse
// telemetry from the boat's hardware into the data cache.
package devices

import (
	"fmt"
	"time"

	"telemetryserver/internal/data"
	"telemetryserver/internal/serialio"
)

// Device is the common interface the serial manager drives.
type Device interface {
	PortName() string
	IsOpen() bool
	Close()
	// Update reads new serial data, parses it, and sends any responses.
	Update()
}

// GenericSerialDevice is the embedded base for all serial devices
// (port of GenericSerialDevice.py).
type GenericSerialDevice struct {
	open     bool
	portName string
	baudRate int
	buffer   []byte
	cache    *data.DataCache
	port     serialio.Port
}

// NewGenericSerialDevice opens the port; on failure the device is created in
// the closed state, matching the Python behavior.
func NewGenericSerialDevice(provider serialio.Provider, cache *data.DataCache, portName string, baudRate int) *GenericSerialDevice {
	g := &GenericSerialDevice{
		portName: portName,
		baudRate: baudRate,
		cache:    cache,
	}
	fmt.Printf("[Serial Device] Opened serial connection on port %s, with baud rate %d.\n", portName, baudRate)
	port, err := provider.Open(portName, baudRate)
	if err != nil {
		fmt.Println("[Serial Device] Failed to open device!")
		g.open = false
		return g
	}
	g.port = port
	g.open = true
	return g
}

// PortName returns the port this device was opened on.
func (g *GenericSerialDevice) PortName() string { return g.portName }

// IsOpen reports whether the device connection is usable.
func (g *GenericSerialDevice) IsOpen() bool {
	return g.open && g.port != nil && g.port.IsOpen()
}

// Close shuts the serial connection.
func (g *GenericSerialDevice) Close() {
	fmt.Printf("[Serial Device] Closed serial connection on port %s.\n", g.portName)
	if g.open {
		g.port.Close()
		g.open = false
	}
}

// Update is a no-op on the base device.
func (g *GenericSerialDevice) Update() {}

// readAvailable appends all currently available bytes to the device buffer.
func (g *GenericSerialDevice) readAvailable() error {
	n, err := g.port.InWaiting()
	if err != nil {
		return err
	}
	if n == 0 {
		return nil
	}
	chunk := make([]byte, n)
	read, err := g.port.Read(chunk)
	if err != nil {
		return err
	}
	g.buffer = append(g.buffer, chunk[:read]...)
	return nil
}

// discardToHeader drops leading bytes until the buffer starts with the header
// byte or is empty (removes invalid packets, old data, etc).
func (g *GenericSerialDevice) discardToHeader(header byte) {
	i := 0
	for i < len(g.buffer) && g.buffer[i] != header {
		i++
	}
	g.buffer = g.buffer[i:]
}

func millis() float64 {
	return float64(time.Now().UnixNano()) / 1e6
}
