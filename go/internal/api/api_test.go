package api

import (
	"encoding/json"
	"io"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"

	"telemetryserver/internal/config"
	"telemetryserver/internal/data"
	"telemetryserver/internal/stats"
)

func get(t *testing.T, cache *data.DataCache, path string) (string, string) {
	t.Helper()
	server := httptest.NewServer(Handler(cache))
	defer server.Close()
	resp, err := server.Client().Get(server.URL + path)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		t.Fatalf("GET %s -> %d", path, resp.StatusCode)
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatal(err)
	}
	return string(body), resp.Header.Get("Access-Control-Allow-Origin")
}

func TestLiveEndpoint(t *testing.T) {
	stats.Reset()
	cache := data.NewDataCache(config.DataKeys)
	cache.Set("batteryVoltage", 36.5)
	cache.Set("batteryVoltage", 35.25)

	body, cors := get(t, cache, "/live")
	if cors != "*" {
		t.Fatal("missing CORS header")
	}

	var parsed map[string]map[string]any
	if err := json.Unmarshal([]byte(body), &parsed); err != nil {
		t.Fatalf("response is not valid JSON: %v\n%s", err, body)
	}
	if len(parsed) != len(config.DataKeys) {
		t.Fatalf("keys = %d, want %d", len(parsed), len(config.DataKeys))
	}
	bv := parsed["batteryVoltage"]
	if bv["current"] != 35.25 || bv["min"] != 35.25 || bv["max"] != 36.5 {
		t.Fatalf("batteryVoltage = %v", bv)
	}
	// Unset values render as the string "None", exactly like the Python API.
	if parsed["motorRpm"]["current"] != "None" {
		t.Fatalf(`motorRpm current = %v, want "None"`, parsed["motorRpm"]["current"])
	}
}

func TestSetEndpoint(t *testing.T) {
	stats.Reset()
	cache := data.NewDataCache(config.DataKeys)
	body, _ := get(t, cache, "/set?key=throttle&value=42.5")
	if body != "42.5" {
		t.Fatalf("body = %q", body)
	}
	if v := cache.GetNumerical("throttle", -1); v != 42.5 {
		t.Fatalf("throttle = %v", v)
	}
}

func TestLiveFormattedEndpoint(t *testing.T) {
	stats.Reset()
	cache := data.NewDataCache(config.DataKeys)
	cache.Set("batteryVoltage", 36.256)
	cache.Set("motorRpm", 3120.6)

	body, _ := get(t, cache, "/live_formatted")
	var parsed map[string]json.RawMessage
	if err := json.Unmarshal([]byte(body), &parsed); err != nil {
		t.Fatalf("response is not valid JSON: %v\n%s", err, body)
	}

	var voltage struct {
		Current    string  `json:"current"`
		MinMax     string  `json:"min_max"`
		CurrentNum float64 `json:"currentNum"`
	}
	if err := json.Unmarshal(parsed["batteryVoltage"], &voltage); err != nil {
		t.Fatal(err)
	}
	if voltage.Current != "36.26 V" {
		t.Fatalf("current = %q, want %q", voltage.Current, "36.26 V")
	}
	if voltage.MinMax != "min: 36.26 V / max: 36.26 V" {
		t.Fatalf("min_max = %q", voltage.MinMax)
	}
	if voltage.CurrentNum != 36.256 {
		t.Fatalf("currentNum = %v", voltage.CurrentNum)
	}

	var rpm struct {
		Current string `json:"current"`
	}
	if err := json.Unmarshal(parsed["motorRpm"], &rpm); err != nil {
		t.Fatal(err)
	}
	// 0 decimals renders as integer with units
	if rpm.Current != "3121 rpm" {
		t.Fatalf("motorRpm current = %q", rpm.Current)
	}

	var unset struct {
		Current string `json:"current"`
		MinMax  string `json:"min_max"`
	}
	if err := json.Unmarshal(parsed["gpsLatitude"], &unset); err != nil {
		t.Fatal(err)
	}
	if unset.Current != "---" || unset.MinMax != "min: --- / max: ---" {
		t.Fatalf("unset key rendered as %+v", unset)
	}

	var status string
	if err := json.Unmarshal(parsed["status"], &status); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(status, "No Radio Link") || !strings.Contains(status, "active devices") {
		t.Fatalf("status = %q", status)
	}
}

func TestStatsEndpoint(t *testing.T) {
	stats.Reset()
	stats.SetNumActiveDevices(3)
	cache := data.NewDataCache(config.DataKeys)
	cache.Set("batteryVoltage", 36)

	body, _ := get(t, cache, "/stats")
	var parsed map[string]string
	if err := json.Unmarshal([]byte(body), &parsed); err != nil {
		t.Fatalf("response is not valid JSON: %v\n%s", err, body)
	}
	// All values are strings formatted like Python's str(), including booleans.
	if parsed["hasRadio"] != "False" {
		t.Fatalf("hasRadio = %q", parsed["hasRadio"])
	}
	if parsed["numActiveDevices"] != "3" {
		t.Fatalf("numActiveDevices = %q", parsed["numActiveDevices"])
	}
	if parsed["activeSession"] != "None" {
		t.Fatalf("activeSession = %q", parsed["activeSession"])
	}
	if parsed["numDataKeys"] != strconv.Itoa(len(config.DataKeys)) {
		t.Fatalf("numDataKeys = %q", parsed["numDataKeys"])
	}
	if parsed["numDataPoints"] != "1" {
		t.Fatalf("numDataPoints = %q", parsed["numDataPoints"])
	}
}

func TestAlarmsEndpoint(t *testing.T) {
	stats.Reset()
	cache := data.NewDataCache(config.DataKeys)

	body, _ := get(t, cache, "/alarms")
	var parsed map[string]struct {
		Key      string   `json:"key"`
		Desc     string   `json:"desc"`
		Value    *float64 `json:"value"`
		RangeMin float64  `json:"range_min"`
		RangeMax float64  `json:"range_max"`
		State    bool     `json:"state"`
	}
	if err := json.Unmarshal([]byte(body), &parsed); err != nil {
		t.Fatalf("response is not valid JSON: %v\n%s", err, body)
	}
	if len(parsed) != len(config.AlarmThresholds) {
		t.Fatalf("alarms = %d, want %d", len(parsed), len(config.AlarmThresholds))
	}
	va := parsed["alarmVoltageRange"]
	if va.Key != "batteryVoltage" || va.RangeMin != 32 || va.RangeMax != 40 {
		t.Fatalf("alarmVoltageRange = %+v", va)
	}
	if va.Value != nil || va.State {
		t.Fatal("alarm with no data must be off with null value")
	}

	// Trip the alarm and check the refreshed state.
	cache.Set("batteryVoltage", 45)
	body, _ = get(t, cache, "/alarms")
	if err := json.Unmarshal([]byte(body), &parsed); err != nil {
		t.Fatal(err)
	}
	va = parsed["alarmVoltageRange"]
	if va.Value == nil || *va.Value != 45 || !va.State {
		t.Fatalf("tripped alarm = %+v", va)
	}
}

func TestStatsRawEndpoint(t *testing.T) {
	stats.Reset()
	cache := data.NewDataCache(config.DataKeys)
	body, _ := get(t, cache, "/stats_raw")
	if body != "test" {
		t.Fatalf("body = %q", body)
	}
}

func TestFormatNumber(t *testing.T) {
	cases := []struct {
		in   float64
		want string
	}{
		{0, "0"},
		{35.5, "35.5"},
		{-1500, "-1500"},
		{0.001, "0.001"},
	}
	for _, tc := range cases {
		if got := formatNumber(tc.in); got != tc.want {
			t.Fatalf("formatNumber(%v) = %q, want %q", tc.in, got, tc.want)
		}
	}
}
