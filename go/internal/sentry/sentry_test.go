package sentry

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

type recordingLED struct {
	states []bool
}

func (r *recordingLED) Set(on bool) error {
	r.states = append(r.states, on)
	return nil
}

func TestBlinksPerConnectedDevice(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, `{"hasRadio" : "False", "numActiveDevices" : "3"}`)
	}))
	defer server.Close()

	led := &recordingLED{}
	var slept time.Duration
	s := New(server.URL, led, func(d time.Duration) { slept += d })
	s.RunOnce()

	// 3 devices -> 3 fast blinks -> 6 LED transitions (on/off pairs).
	if len(led.states) != 6 {
		t.Fatalf("LED transitions = %d, want 6", len(led.states))
	}
	for i, on := range led.states {
		if on != (i%2 == 0) {
			t.Fatalf("transition %d = %v; blinks must alternate on/off", i, on)
		}
	}
	if slept != 6*100*time.Millisecond+time.Second {
		t.Fatalf("slept %v", slept)
	}
}

func TestSlowBlinkWhenServerDown(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	server.Close() // no server listening

	led := &recordingLED{}
	var slept time.Duration
	s := New(server.URL, led, func(d time.Duration) { slept += d })
	s.RunOnce()

	// Down -> 5 slow blinks -> 10 transitions, 10 seconds of sleeping.
	if len(led.states) != 10 {
		t.Fatalf("LED transitions = %d, want 10", len(led.states))
	}
	if slept != 10*time.Second {
		t.Fatalf("slept %v", slept)
	}
}

func TestMalformedStatsTreatedAsDown(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, `not json`)
	}))
	defer server.Close()

	led := &recordingLED{}
	s := New(server.URL, led, func(time.Duration) {})
	s.RunOnce()
	if len(led.states) != 10 {
		t.Fatalf("LED transitions = %d, want 10 (slow blink)", len(led.states))
	}
}
