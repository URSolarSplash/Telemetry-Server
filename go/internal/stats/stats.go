// Package stats stores statistic variables as globals (port of server/statistics.py).
// Unlike the Python original, access is mutex-guarded because the HTTP API and
// the main loop touch these from different goroutines.
package stats

import (
	"fmt"
	"sync"
)

var (
	mu                    sync.Mutex
	hasRadio              bool
	numDataPoints         int
	numRadioPackets       int
	numActiveDevices      int
	activeSession         *string
	numDroppedNodePackets int
	numDataKeys           *int
)

// Reset restores all statistics to their initial values (used by tests).
func Reset() {
	mu.Lock()
	defer mu.Unlock()
	hasRadio = false
	numDataPoints = 0
	numRadioPackets = 0
	numActiveDevices = 0
	activeSession = nil
	numDroppedNodePackets = 0
	numDataKeys = nil
}

func SetHasRadio(v bool) { mu.Lock(); hasRadio = v; mu.Unlock() }

func HasRadio() bool { mu.Lock(); defer mu.Unlock(); return hasRadio }

func IncDataPoints() { mu.Lock(); numDataPoints++; mu.Unlock() }

func NumDataPoints() int { mu.Lock(); defer mu.Unlock(); return numDataPoints }

func IncDroppedNodePackets() { mu.Lock(); numDroppedNodePackets++; mu.Unlock() }

func NumDroppedNodePackets() int { mu.Lock(); defer mu.Unlock(); return numDroppedNodePackets }

func SetNumActiveDevices(v int) { mu.Lock(); numActiveDevices = v; mu.Unlock() }

func NumActiveDevices() int { mu.Lock(); defer mu.Unlock(); return numActiveDevices }

func NumRadioPackets() int { mu.Lock(); defer mu.Unlock(); return numRadioPackets }

func SetActiveSession(name string) { mu.Lock(); activeSession = &name; mu.Unlock() }

// SetNumDataKeys mirrors the Python /stats handler, which lazily adds the
// numDataKeys entry to the stats dict on first request.
func SetNumDataKeys(v int) { mu.Lock(); numDataKeys = &v; mu.Unlock() }

// Pair is one stats entry with its value already formatted the way Python's
// str() would render it ("True"/"False" for booleans, "None" for null).
type Pair struct {
	Key   string
	Value string
}

// Snapshot returns the statistics in the Python dict insertion order.
func Snapshot() []Pair {
	mu.Lock()
	defer mu.Unlock()
	pyBool := func(b bool) string {
		if b {
			return "True"
		}
		return "False"
	}
	session := "None"
	if activeSession != nil {
		session = *activeSession
	}
	pairs := []Pair{
		{"hasRadio", pyBool(hasRadio)},
		{"numDataPoints", fmt.Sprintf("%d", numDataPoints)},
		{"numRadioPackets", fmt.Sprintf("%d", numRadioPackets)},
		{"numActiveDevices", fmt.Sprintf("%d", numActiveDevices)},
		{"activeSession", session},
		{"numDroppedNodePackets", fmt.Sprintf("%d", numDroppedNodePackets)},
	}
	if numDataKeys != nil {
		pairs = append(pairs, Pair{"numDataKeys", fmt.Sprintf("%d", *numDataKeys)})
	}
	return pairs
}
