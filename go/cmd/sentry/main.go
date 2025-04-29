// Sentry monitors the telemetry server status (port of sentry.py).
// It blinks a GPIO LED on the telemetry server box:
//   - server down: slow 1s blinks
//   - server up:   one fast blink per connected device
//
// Runs as a separate service on the Pi. RPi.GPIO board pin 32 corresponds to
// BCM GPIO 12, driven here via the sysfs GPIO interface. With -console the
// LED is printed to stdout instead, so the logic runs anywhere.
package main

import (
	"flag"
	"fmt"
	"time"

	"telemetryserver/internal/sentry"
)

func main() {
	gpio := flag.Int("gpio", 12, "BCM GPIO number of the status LED (board pin 32)")
	console := flag.Bool("console", false, "print LED state to stdout instead of driving GPIO")
	statsURL := flag.String("url", "http://localhost:5000/stats", "telemetry server stats endpoint")
	flag.Parse()

	var led sentry.LED
	if *console {
		led = sentry.ConsoleLED{}
	} else {
		sysfsLED, err := sentry.NewSysfsLED(*gpio)
		if err != nil {
			fmt.Println("[Sentry] Failed to open GPIO, falling back to console:", err)
			led = sentry.ConsoleLED{}
		} else {
			led = sysfsLED
		}
	}

	s := sentry.New(*statsURL, led, time.Sleep)
	for {
		s.RunOnce()
	}
}
