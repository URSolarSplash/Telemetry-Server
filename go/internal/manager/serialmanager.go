// Package manager ports server/serialManager.py: scanning for USB serial
// devices, opening the right driver for each, and polling them.
package manager

import (
	"fmt"
	"strings"

	"telemetryserver/internal/config"
	"telemetryserver/internal/data"
	"telemetryserver/internal/devices"
	"telemetryserver/internal/serialio"
	"telemetryserver/internal/stats"
)

// SerialManager is responsible for managing serial devices.
type SerialManager struct {
	cache           *data.DataCache
	provider        serialio.Provider
	devices         []devices.Device
	deviceBlacklist []string
	lastScan        float64
	lastPoll        float64
}

// NewSerialManager creates a manager scanning ports from the given provider.
func NewSerialManager(cache *data.DataCache, provider serialio.Provider) *SerialManager {
	return &SerialManager{
		cache:           cache,
		provider:        provider,
		deviceBlacklist: config.PortBlacklist,
		lastScan:        data.Now(),
		lastPoll:        data.Now(),
	}
}

// Devices returns the currently connected devices (for tests/stats).
func (m *SerialManager) Devices() []devices.Device {
	return m.devices
}

// Shutdown closes all devices.
func (m *SerialManager) Shutdown() {
	for _, device := range m.devices {
		device.Close()
	}
	fmt.Println("[Serial Manager] shutdown complete.")
}

// UpdateDevices scans the serial ports, connects to new devices, and drops
// devices that disappeared or errored out. Rate limited to config.ScanRate.
func (m *SerialManager) UpdateDevices() {
	if data.Now()-m.lastScan < config.ScanRate {
		return
	}
	m.lastScan = data.Now()

	// Update number of live devices
	stats.SetNumActiveDevices(len(m.devices))

	portList, err := m.provider.ListPorts()
	if err != nil {
		fmt.Println("[Serial Manager] Race condition during port scan. Skipping scan...")
		return
	}

	// Debug: Ignore devices
	if config.IgnoreDevices {
		portList = nil
	}

	portNames := make(map[string]bool, len(portList))
	for _, port := range portList {
		portNames[port.Name] = true
		portAlreadyOpen := false
		for _, device := range m.devices {
			if device.PortName() == port.Name {
				portAlreadyOpen = true
			}
		}
		if portAlreadyOpen {
			continue
		}

		// We have found a new device.
		// Exit early if the device ID is blacklisted.
		blacklisted := false
		for _, b := range m.deviceBlacklist {
			if port.Name == b {
				blacklisted = true
			}
		}
		if blacklisted {
			continue
		}

		fmt.Printf("[Serial Manager] detected new device id=%s, desc=%s\n", port.Name, port.Description)

		// This device is one of the following:
		// - Victron BMV device
		// - Telemetry Protocol device
		// - Radio serial
		// We use the USB-Serial description field to determine this. If the
		// description matches a known hardware device, we use the custom
		// protocol, otherwise we use the standard telemetry protocol.
		var deviceInstance devices.Device
		switch {
		case strings.HasPrefix(port.Description, "FT231X"):
			// USB Radio Telemetry
			fmt.Println("[Serial Manager] Detected Device Type: USB Radio Telemetry")
			radioDevice := devices.NewRadioDevice(m.provider, m.cache, port.Name)
			deviceInstance = radioDevice
			// Turn on radio flag in statistics
			stats.SetHasRadio(true)
			// Set data cache to link to radio object
			m.cache.SetRadioDevice(radioDevice)
			// Disable control algorithms for this session (slave mode).
			fmt.Println("[Serial Manager] Setting config to slave mode for duration of this session! Control algorithms disabled.")
			config.IsSlave = true
		case strings.HasPrefix(port.Description, "VE Direct"):
			fmt.Println("[Serial Manager] Detected Device Type: Victron VE-Direct Device")
			deviceInstance = devices.NewVictronDevice(m.provider, m.cache, port.Name)
		case strings.HasPrefix(port.Description, "ChibiOS"):
			fmt.Println("[Serial Manager] Detected Device Type: VESC Motor Controller")
			deviceInstance = devices.NewVescDevice(m.provider, m.cache, port.Name)
		default:
			fmt.Println("[Serial Manager] Detected Device Type: Default Telemetry")
			deviceInstance = devices.NewStatelessTelemetryNodeDevice(m.provider, m.cache, port.Name)
		}

		// Add newly opened device to the list
		m.devices = append(m.devices, deviceInstance)
	}

	// Remove serial devices that have been closed, identified by the serial
	// device being closed or not showing up on the serial scan.
	// (The Python version mutated the list during iteration, which skipped
	// the next device after a removal; this rebuild handles all of them.)
	kept := m.devices[:0]
	for _, device := range m.devices {
		if portNames[device.PortName()] && device.IsOpen() {
			kept = append(kept, device)
			continue
		}
		if device.IsOpen() {
			device.Close()
		}
		switch device.(type) {
		case *devices.RadioDevice:
			stats.SetHasRadio(false)
			m.cache.SetRadioDevice(nil)
		case *devices.StatelessTelemetryNodeDevice:
			m.cache.Set("throttleEnabled", 0)
			m.cache.Set("throttle", 0)
		}
	}
	m.devices = kept
}

// PollDevices gets data from the active device list. Rate limited to
// config.PollRate.
func (m *SerialManager) PollDevices() {
	if data.Now()-m.lastPoll < config.PollRate {
		return
	}
	m.lastPoll = data.Now()

	for _, device := range m.devices {
		if device.IsOpen() {
			device.Update()
		}
	}
}
