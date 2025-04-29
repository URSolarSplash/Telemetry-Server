// Package api ports server/api.py: the lightweight HTTP interface for
// reading live telemetry and writing data points.
//
// The JSON is built by hand, exactly like the Flask version, so that quirks
// existing clients depend on are preserved (e.g. missing values render as the
// string "None" in /live and "---" in /live_formatted).
package api

import (
	"fmt"
	"math"
	"net/http"
	"strconv"
	"strings"

	"telemetryserver/internal/config"
	"telemetryserver/internal/data"
	"telemetryserver/internal/stats"
)

// formatNumber renders a float like Python's str(): shortest representation,
// with integral values as plain integers.
func formatNumber(v float64) string {
	if v == math.Trunc(v) && math.Abs(v) < 1e15 {
		return strconv.FormatInt(int64(v), 10)
	}
	return strconv.FormatFloat(v, 'g', -1, 64)
}

// pythonRound rounds half-to-even to a number of decimals, like Python's round().
func pythonRound(v float64, decimals int) float64 {
	scale := math.Pow(10, float64(decimals))
	return math.RoundToEven(v*scale) / scale
}

// formatRounded renders a value rounded to the key's decimal places with its
// units appended, matching the /live_formatted logic.
func formatRounded(v float64, decimals int, units string) string {
	rounded := pythonRound(v, decimals)
	if decimals == 0 {
		return fmt.Sprintf("%d%s", int(rounded), units)
	}
	return formatNumber(rounded) + units
}

// Handler builds the API http.Handler around a data cache.
func Handler(cache *data.DataCache) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/live", func(w http.ResponseWriter, r *http.Request) {
		var b strings.Builder
		b.WriteString("{")
		for i, key := range cache.GetKeys() {
			if i > 0 {
				b.WriteString(",\n")
			} else {
				b.WriteString("\n")
			}
			currentValue := "\"None\""
			if v, ok := cache.Get(key); ok {
				currentValue = formatNumber(v)
			}
			minValue := "\"None\""
			if v, ok := cache.GetMin(key); ok {
				minValue = formatNumber(v)
			}
			maxValue := "\"None\""
			if v, ok := cache.GetMax(key); ok {
				maxValue = formatNumber(v)
			}
			fmt.Fprintf(&b, "  \"%s\" : {\"current\" : %s, \"min\" : %s, \"max\" : %s}", key, currentValue, minValue, maxValue)
		}
		b.WriteString("\n}")
		writeJSON(w, b.String())
	})

	mux.HandleFunc("/set", func(w http.ResponseWriter, r *http.Request) {
		key := r.URL.Query().Get("key")
		value := r.URL.Query().Get("value")
		if key != "" && value != "" {
			if v, err := strconv.ParseFloat(value, 64); err == nil {
				cache.Set(key, v)
			}
		}
		fmt.Fprint(w, value)
	})

	mux.HandleFunc("/stats_raw", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, "test")
	})

	mux.HandleFunc("/live_formatted", func(w http.ResponseWriter, r *http.Request) {
		var b strings.Builder
		b.WriteString("{")
		for i, keyData := range config.DataKeys {
			key := keyData.Name
			if i > 0 {
				b.WriteString(",\n")
			} else {
				b.WriteString("\n")
			}
			currentValue := "---"
			currentValueNumerical := "0"
			if v, ok := cache.Get(key); ok {
				currentValue = formatRounded(v, keyData.Decimals, keyData.Units)
				currentValueNumerical = formatNumber(v)
			}
			minValue := "---"
			if v, ok := cache.GetMin(key); ok {
				minValue = formatRounded(v, keyData.Decimals, keyData.Units)
			}
			maxValue := "---"
			if v, ok := cache.GetMax(key); ok {
				maxValue = formatRounded(v, keyData.Decimals, keyData.Units)
			}
			minMaxValue := fmt.Sprintf("min: %s / max: %s", minValue, maxValue)
			fmt.Fprintf(&b, "  \"%s\" : {\"current\" : \"%s\", \"min_max\" : \"%s\", \"currentNum\" : %s}", key, currentValue, minMaxValue, currentValueNumerical)
		}
		b.WriteString(",\n")
		statusString := ""
		if stats.HasRadio() {
			statusString += "Radio Link Established "
		} else {
			statusString += "No Radio Link "
		}
		statusString += fmt.Sprintf("(%d data points / %d packets / %.1f%% coverage) Status: %d active devices",
			stats.NumDataPoints(), stats.NumRadioPackets(), cache.GetCoveragePercentage(), stats.NumActiveDevices())
		b.WriteString("  \"status\" : \"" + statusString + "\"\n")
		b.WriteString("}")
		writeJSON(w, b.String())
	})

	mux.HandleFunc("/alarms", func(w http.ResponseWriter, r *http.Request) {
		var b strings.Builder
		b.WriteString("{")
		for i, alarm := range cache.GetAlarms() {
			// Update alarms before encoding
			alarm.GetAlarmState()
			if i > 0 {
				b.WriteString(", ")
			}
			value := "null"
			if alarm.HasValue {
				value = formatNumber(alarm.Value)
			}
			fmt.Fprintf(&b, "\"%s\": {\"key\": \"%s\", \"desc\": \"%s\", \"value\": %s, \"range_min\": %s, \"range_max\": %s, \"state\": %t}",
				alarm.ID, alarm.Key, alarm.Description, value, formatNumber(alarm.Min), formatNumber(alarm.Max), alarm.State)
		}
		b.WriteString("}")
		writeJSON(w, b.String())
	})

	mux.HandleFunc("/stats", func(w http.ResponseWriter, r *http.Request) {
		stats.SetNumDataKeys(len(config.DataKeys))
		var b strings.Builder
		b.WriteString("{")
		for i, pair := range stats.Snapshot() {
			if i > 0 {
				b.WriteString(",\n")
			} else {
				b.WriteString("\n")
			}
			fmt.Fprintf(&b, "  \"%s\" : \"%s\"", pair.Key, pair.Value)
		}
		b.WriteString("\n}")
		writeJSON(w, b.String())
	})

	return mux
}

func writeJSON(w http.ResponseWriter, body string) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	fmt.Fprint(w, body)
}

// StartHTTPServerManager starts the API server in a background goroutine
// (port of HTTPServerManager). It listens on 127.0.0.1 like the Python
// WSGIServer configuration.
func StartHTTPServerManager(cache *data.DataCache) {
	fmt.Println("[API] Starting server instance...")
	go func() {
		addr := fmt.Sprintf("127.0.0.1:%d", config.HTTPPort)
		if err := http.ListenAndServe(addr, Handler(cache)); err != nil {
			fmt.Println("[API] server error:", err)
		}
	}()
}
