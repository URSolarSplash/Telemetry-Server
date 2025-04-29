package data

import (
	"fmt"
	"sync"

	"telemetryserver/internal/config"
	"telemetryserver/internal/stats"
)

// RadioOutput is implemented by the radio device so data point writes can be
// mirrored to the parent server (slave mode).
type RadioOutput interface {
	AddToWriteCache(name string, value float64)
}

// DataCache represents a collection of data points for all telemetry items.
// It is safe for concurrent use (HTTP handlers + main loop).
type DataCache struct {
	mu            sync.Mutex
	values        map[string]*DataPoint
	keyToIndexMap map[string]int
	keyList       []config.DataKey

	// Radio object with an AddToWriteCache() function for data points.
	// If set, data point writes are mirrored to this object.
	radioOutputDevice RadioOutput

	alarms []*Alarm
}

// NewDataCache creates blank data points based on the key list.
func NewDataCache(keyList []config.DataKey) *DataCache {
	c := &DataCache{
		values:        make(map[string]*DataPoint, len(keyList)),
		keyToIndexMap: make(map[string]int, len(keyList)),
		keyList:       keyList,
	}
	for i, key := range keyList {
		c.values[key.Name] = NewDataPoint(key.Timeout)
		c.keyToIndexMap[key.Name] = i
	}
	for _, spec := range config.AlarmThresholds {
		c.alarms = append(c.alarms, NewAlarm(c, spec))
	}
	return c
}

// KeyToIndex maps a key name to its index in the key list (radio protocol).
func (c *DataCache) KeyToIndex(key string) (int, bool) {
	i, ok := c.keyToIndexMap[key]
	return i, ok
}

// IndexToKey maps a key list index back to its name (radio protocol).
func (c *DataCache) IndexToKey(index int) (string, bool) {
	if index < 0 || index >= len(c.keyList) {
		return "", false
	}
	return c.keyList[index].Name, true
}

// SetRadioDevice links (or unlinks, with nil) the radio output device.
func (c *DataCache) SetRadioDevice(device RadioOutput) {
	c.mu.Lock()
	c.radioOutputDevice = device
	c.mu.Unlock()
}

// GetCoveragePercentage returns the percentage of keys holding live values.
func (c *DataCache) GetCoveragePercentage() float64 {
	c.mu.Lock()
	defer c.mu.Unlock()
	numValidKeys := 0
	for _, dp := range c.values {
		if !dp.IsExpired() {
			numValidKeys++
		}
	}
	return (float64(numValidKeys) / float64(len(c.keyList))) * 100.0
}

// Set sets a data point if it exists, and mirrors the write over radio when a
// radio device is linked. Unknown keys are logged, matching the Python port.
func (c *DataCache) Set(name string, value float64) {
	c.mu.Lock()
	dp, ok := c.values[name]
	if !ok {
		c.mu.Unlock()
		fmt.Printf("[Tried to set invalid key [%s]]\n", name)
		return
	}
	dp.Set(value)
	radio := c.radioOutputDevice
	c.mu.Unlock()
	if radio != nil && config.WriteFromSlave {
		radio.AddToWriteCache(name, value)
	}
	stats.IncDataPoints()
}

// SetNoRadio sets a data point without mirroring the write over radio.
func (c *DataCache) SetNoRadio(name string, value float64) {
	c.mu.Lock()
	dp, ok := c.values[name]
	if !ok {
		c.mu.Unlock()
		fmt.Printf("[Tried to set invalid key [%s]]\n", name)
		return
	}
	dp.Set(value)
	c.mu.Unlock()
	stats.IncDataPoints()
}

// Get returns a data point's value; ok=false when expired, unset, or unknown.
func (c *DataCache) Get(name string) (float64, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	dp, ok := c.values[name]
	if !ok {
		fmt.Printf("[Tried to get invalid key [%s]]\n", name)
		return 0, false
	}
	return dp.Get()
}

// GetNumerical returns a data point's value, or the default when it has no
// live value or doesn't exist.
func (c *DataCache) GetNumerical(name string, def float64) float64 {
	c.mu.Lock()
	defer c.mu.Unlock()
	dp, ok := c.values[name]
	if !ok {
		fmt.Printf("[Tried to get invalid key [%s]]\n", name)
		return def
	}
	return dp.GetNumerical(def)
}

// GetMin returns a data point's historical minimum value.
func (c *DataCache) GetMin(name string) (float64, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	dp, ok := c.values[name]
	if !ok {
		return 0, false
	}
	return dp.GetMin()
}

// GetMax returns a data point's historical maximum value.
func (c *DataCache) GetMax(name string) (float64, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	dp, ok := c.values[name]
	if !ok {
		return 0, false
	}
	return dp.GetMax()
}

// GetKeys returns the key names in key-list order (Python dict insertion order).
func (c *DataCache) GetKeys() []string {
	keys := make([]string, len(c.keyList))
	for i, k := range c.keyList {
		keys[i] = k.Name
	}
	return keys
}

// HasValidData reports whether any data point currently holds a live value.
func (c *DataCache) HasValidData() bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	for _, dp := range c.values {
		if !dp.IsExpired() {
			return true
		}
	}
	return false
}

// GetAlarms returns the alarms in their configured order.
func (c *DataCache) GetAlarms() []*Alarm {
	return c.alarms
}
