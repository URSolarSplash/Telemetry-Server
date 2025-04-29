// Main telemetry server file (port of main.py).
package main

import (
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"telemetryserver/internal/api"
	"telemetryserver/internal/config"
	"telemetryserver/internal/controls"
	"telemetryserver/internal/dashboard"
	"telemetryserver/internal/data"
	"telemetryserver/internal/manager"
	"telemetryserver/internal/radio"
	"telemetryserver/internal/serialio"
)

// expandUser replaces a leading ~ with the home directory (os.path.expanduser).
func expandUser(path string) string {
	if path == "~" || strings.HasPrefix(path, "~/") {
		home, err := os.UserHomeDir()
		if err == nil {
			return filepath.Join(home, strings.TrimPrefix(path, "~"))
		}
	}
	return path
}

func main() {
	fmt.Println("[Main] Initializing Telemetry Server...")

	// Create base database folder if it doesn't exist
	config.DbFolder = expandUser(config.DbFolder)
	if _, err := os.Stat(config.DbFolder); os.IsNotExist(err) {
		fmt.Println("[Database] Creating base database folder...")
		if err := os.MkdirAll(config.DbFolder, 0o755); err != nil {
			fmt.Println("[Database] Failed to create database folder:", err)
			os.Exit(1)
		}
	}

	// Create a data cache and Database
	// Data cache handles storage of values and their expirations
	// Database connects the data cache to a sqlite file
	dataCache := data.NewDataCache(config.DataKeys)
	database, err := data.NewDatabase(dataCache, filepath.Join(config.DbFolder, config.DbFile), config.DbEraseOnStart)
	if err != nil {
		fmt.Println("[Database] Failed to open database:", err)
		os.Exit(1)
	}

	// Set timestamp to start at 0 at program start
	// If you don't call this, the timestamp is since epoch
	database.ResetTimestamp()

	// Create manager classes for several functions:
	// - Serial manager is responsible for managing serial devices
	// - Radio manager is responsible for radio-based data transmission to shore
	// - HTTP server manager creates a lightweight interface to get the latest data via GET request.
	provider := serialio.SystemProvider{}
	serialMgr := manager.NewSerialManager(dataCache, provider)
	radioMgr := radio.NewRadioManager(dataCache, provider)
	api.StartHTTPServerManager(dataCache)
	dashboardMgr := dashboard.NewManager(".")

	// Set up control algorithms manager
	controlAlgorithms := controls.NewControlAlgorithms(dataCache)

	fmt.Println("[Main] Telemetry Server Initialized.")

	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, os.Interrupt, syscall.SIGTERM)

loop:
	for {
		select {
		case <-sigs:
			fmt.Println("\n[Main] Shutting down...")
			break loop
		default:
		}

		// Update the device list and connect to new devices
		// Also disconnect from devices which have timed out
		serialMgr.UpdateDevices()

		// Polls active devices that want new data
		// Sends a packet which requests more data
		serialMgr.PollDevices()

		// Update radio communication
		// Sends radio packets at a fixed rate
		radioMgr.Update()

		// If the data cache has valid data, save into the database
		if dataCache.HasValidData() {
			if err := database.SaveData(); err != nil {
				fmt.Println("[Database] save error:", err)
			}
		}

		// Update control algorithms
		if !config.IsSlave {
			controlAlgorithms.Update()
		}

		// The Python loop spun as fast as possible; a short sleep keeps the
		// same behavior (all work is rate limited internally) without
		// pinning a CPU core.
		time.Sleep(time.Millisecond)
	}

	serialMgr.Shutdown()
	radioMgr.Shutdown()
	database.Shutdown()
	dashboardMgr.Shutdown()
}
