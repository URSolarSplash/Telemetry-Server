# Telemetry Server (Go port)

A complete Go port of the Python telemetry server, as planned in the main
README ("Rewrite telemetry server in Go"). It builds to a single fully static
binary — no Python, pip packages, or shared libraries needed on the Pi.

## Layout

| Go package | Ports |
|---|---|
| `cmd/telemetry-server` | `main.py` |
| `cmd/sentry` | `sentry.py` (GPIO status LED; `-console` mode runs anywhere) |
| `internal/config` | `server/config.py` |
| `internal/stats` | `server/statistics.py` |
| `internal/data` | `server/data.py` (DataPoint, DataCache, SQLite Database) + `server/alarms.py` |
| `internal/api` | `server/api.py` (`/live`, `/live_formatted`, `/set`, `/stats`, `/stats_raw`, `/alarms` on :5000) |
| `internal/dashboard` | `server/dashboard.py` (static file server on :5001) |
| `internal/controls` | `server/controls.py` |
| `internal/manager` | `server/serialManager.py` |
| `internal/radio` | `server/radio.py` |
| `internal/devices` | `server/devices/` (stateless node, Victron VE.Direct, VESC, radio) |
| `internal/vesc` | the `pyvesc` subset the server used (CRC16 framing, GET_VALUES, SET_DUTY, SET_CURRENT) |
| `internal/radioproto` | the shared 6-byte radio packet format |
| `internal/serialio` | serial ports behind an interface: real hardware (`go.bug.st/serial`) or in-memory fakes for tests |

SQLite uses `modernc.org/sqlite` (pure Go), so `CGO_ENABLED=0` builds work.
The HTTP endpoints reproduce the Python responses byte-format-compatibly
(including `"None"` strings in `/live` and stringified stats), so the web
dashboard, OpenGL dashboard, and sentry all keep working unmodified.

## Build

```sh
cd go
CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o bin/telemetry-server ./cmd/telemetry-server
CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o bin/sentry ./cmd/sentry
```

Cross-compile for the Raspberry Pi:

```sh
# Pi Zero / 1 (ARMv6)
CGO_ENABLED=0 GOOS=linux GOARCH=arm GOARM=6 go build -o bin/telemetry-server-rpi ./cmd/telemetry-server
# Pi 3/4/5 64-bit OS
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o bin/telemetry-server-rpi64 ./cmd/telemetry-server
```

Run from the repository root (so the dashboard file server can serve
`dashboard/`), same as `python3 main.py`:

```sh
./go/bin/telemetry-server
```

## Testing without sensors or a Raspberry Pi

All hardware is abstracted behind `serialio.Provider`; the test suite plugs
in-memory fake serial ports into the real drivers and feeds them real
protocol bytes:

- unit tests for every package (data expiry, checksums, VE.Direct blocks,
  VESC frames, radio packets, controls state machine, alarms, every HTTP
  endpoint, SQLite sessions),
- `internal/integration` boots the whole server against a simulated boat
  (throttle node + Victron + VESC), checks values end-to-end through the HTTP
  API and the SQLite file, then unplugs everything,
- a boat↔shore radio-link test couples a `RadioManager` to a shore server's
  `RadioDevice` and verifies telemetry downlink and command write-back.

```sh
cd go
go test ./...        # full suite
go test -race ./...  # with the race detector
```

## Intentional differences from the Python version

- The main loop sleeps 1 ms per iteration instead of busy-spinning.
- Removing multiple unplugged devices in one scan works reliably (the Python
  version mutated the device list while iterating over it, skipping items).
- The serial manager, HTTP handlers, and data cache are goroutine-safe.
- `pyvesc`'s GET_VALUES decoding is implemented against the standard VESC
  FW 3.x field layout; verify scaling against your VESC firmware before
  relying on absolute values.
- `sentry` drives the LED via sysfs GPIO (BCM 12 = board pin 32) and gains a
  `-console` flag.
