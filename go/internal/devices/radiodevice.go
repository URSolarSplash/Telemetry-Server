package devices

import (
	"fmt"
	"sync"

	"telemetryserver/internal/config"
	"telemetryserver/internal/data"
	"telemetryserver/internal/radioproto"
	"telemetryserver/internal/serialio"
)

// RadioDevice is the shore-side USB radio telemetry link (port of
// RadioDevice.py). It receives data point packets from the boat and mirrors
// local writes back at a fixed rate.
type RadioDevice struct {
	*GenericSerialDevice
	lastUpdate float64

	mu         sync.Mutex
	writeCache map[string]float64
}

func NewRadioDevice(provider serialio.Provider, cache *data.DataCache, portName string) *RadioDevice {
	return &RadioDevice{
		GenericSerialDevice: NewGenericSerialDevice(provider, cache, portName, 57600),
		lastUpdate:          data.Now(),
		writeCache:          make(map[string]float64),
	}
}

func (d *RadioDevice) Update() {
	if d.open {
		if err := d.readAvailable(); err != nil {
			fmt.Println(err)
			d.Close()
		} else {
			d.discardToHeader(radioproto.Header)
			if len(d.buffer) >= radioproto.PacketSize {
				packet := d.buffer[0:radioproto.PacketSize:radioproto.PacketSize]
				d.buffer = d.buffer[radioproto.PacketSize:]
				d.read(packet)
			}
		}
	}

	// Sends packets at a fixed rate: each time it checks the write cache and
	// if there are new packets, writes them.
	if data.Now()-d.lastUpdate < config.RadioPacketRate {
		return
	}
	d.lastUpdate = data.Now()
	d.mu.Lock()
	pending := d.writeCache
	d.writeCache = make(map[string]float64)
	d.mu.Unlock()
	for key, value := range pending {
		d.write(key, value)
	}
}

// AddToWriteCache queues a local data point write for transmission back to
// the parent server. Called from the data cache (any goroutine).
func (d *RadioDevice) AddToWriteCache(name string, value float64) {
	d.mu.Lock()
	d.writeCache[name] = value
	d.mu.Unlock()
}

// read parses a received packet into the cache (without re-transmitting).
func (d *RadioDevice) read(packet []byte) {
	dataID, value, hasValue := radioproto.Decode(packet)
	dataKey, ok := d.cache.IndexToKey(dataID)
	if !ok || !hasValue {
		return
	}
	d.cache.SetNoRadio(dataKey, value)
}

// write sends a data point update to the radio stream.
func (d *RadioDevice) write(dataName string, dataValue float64) {
	dataID, ok := d.cache.KeyToIndex(dataName)
	if !ok {
		return
	}
	if _, err := d.port.Write(radioproto.Encode(dataID, dataValue, true)); err != nil {
		fmt.Println("Failed to write radio packet from Slave.")
		fmt.Println(err)
	}
}
