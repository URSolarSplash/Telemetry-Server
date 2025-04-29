// Package sentry implements the status LED logic from sentry.py: poll the
// telemetry server's /stats endpoint and blink an LED accordingly.
package sentry

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"time"
)

// LED abstracts the status output so the blink logic is testable without a Pi.
type LED interface {
	Set(on bool) error
}

// ConsoleLED prints the LED state to stdout.
type ConsoleLED struct{}

func (ConsoleLED) Set(on bool) error {
	if on {
		fmt.Println("[LED] ON")
	} else {
		fmt.Println("[LED] OFF")
	}
	return nil
}

// SysfsLED drives a GPIO output through /sys/class/gpio.
type SysfsLED struct {
	valuePath string
}

// NewSysfsLED exports the given BCM GPIO and configures it as an output.
func NewSysfsLED(bcm int) (*SysfsLED, error) {
	gpio := strconv.Itoa(bcm)
	base := "/sys/class/gpio/gpio" + gpio
	if _, err := os.Stat(base); os.IsNotExist(err) {
		if err := os.WriteFile("/sys/class/gpio/export", []byte(gpio), 0o644); err != nil {
			return nil, err
		}
		// The kernel needs a moment to create the pin's sysfs nodes.
		time.Sleep(100 * time.Millisecond)
	}
	if err := os.WriteFile(base+"/direction", []byte("out"), 0o644); err != nil {
		return nil, err
	}
	return &SysfsLED{valuePath: base + "/value"}, nil
}

func (l *SysfsLED) Set(on bool) error {
	v := "0"
	if on {
		v = "1"
	}
	return os.WriteFile(l.valuePath, []byte(v), 0o644)
}

// Sentry polls the stats endpoint and blinks the LED.
type Sentry struct {
	statsURL string
	led      LED
	sleep    func(time.Duration)
	client   *http.Client
}

// New creates a Sentry; sleep is injectable so tests run instantly.
func New(statsURL string, led LED, sleep func(time.Duration)) *Sentry {
	return &Sentry{
		statsURL: statsURL,
		led:      led,
		sleep:    sleep,
		client:   &http.Client{Timeout: 2 * time.Second},
	}
}

// RunOnce polls the server once and performs one blink cycle.
func (s *Sentry) RunOnce() {
	status := 0
	numDevices := 0
	resp, err := s.client.Get(s.statsURL)
	if err == nil {
		func() {
			defer resp.Body.Close()
			if resp.StatusCode != http.StatusOK {
				return
			}
			var packet map[string]string
			if json.NewDecoder(resp.Body).Decode(&packet) != nil {
				return
			}
			n, err := strconv.Atoi(packet["numActiveDevices"])
			if err != nil {
				return
			}
			// Server is up
			status = 1
			numDevices = n
		}()
	}

	if status == 0 {
		// Blink slowly since the telemetry is off
		for i := 0; i < 5; i++ {
			s.led.Set(true)
			s.sleep(time.Second)
			s.led.Set(false)
			s.sleep(time.Second)
		}
	} else {
		// Blink a number of times representing the number of devices connected
		for i := 0; i < numDevices; i++ {
			s.led.Set(true)
			s.sleep(100 * time.Millisecond)
			s.led.Set(false)
			s.sleep(100 * time.Millisecond)
		}
		s.sleep(time.Second)
	}
}
