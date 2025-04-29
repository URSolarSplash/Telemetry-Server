// Package serialio abstracts serial port access behind interfaces so the
// telemetry server can run against real hardware (go.bug.st/serial) or
// in-memory fakes for testing without sensors or a Raspberry Pi.
package serialio

import (
	"fmt"
	"sync"

	"go.bug.st/serial"
	"go.bug.st/serial/enumerator"
)

// PortInfo describes a discovered serial port, mirroring the (device,
// description) tuple from pyserial's list_ports.comports().
type PortInfo struct {
	Name        string
	Description string
}

// Port is a non-blocking serial connection, modeled on the pyserial API the
// Python server relied on (in_waiting + read/write with zero timeout).
type Port interface {
	// InWaiting returns the number of bytes available to read without blocking.
	InWaiting() (int, error)
	// Read reads up to len(p) of the already-available bytes without blocking.
	Read(p []byte) (int, error)
	Write(p []byte) (int, error)
	Close() error
	// IsOpen reports whether the connection is still usable.
	IsOpen() bool
}

// Provider lists and opens serial ports. The real implementation talks to the
// OS; tests substitute a FakeProvider.
type Provider interface {
	ListPorts() ([]PortInfo, error)
	Open(name string, baudRate int) (Port, error)
}

// SystemProvider is the real-hardware Provider backed by go.bug.st/serial.
type SystemProvider struct{}

// ListPorts enumerates serial ports with USB product descriptions where
// available (equivalent to serial.tools.list_ports.comports()).
func (SystemProvider) ListPorts() ([]PortInfo, error) {
	details, err := enumerator.GetDetailedPortsList()
	if err != nil {
		return nil, err
	}
	infos := make([]PortInfo, 0, len(details))
	for _, d := range details {
		desc := d.Product
		if desc == "" {
			desc = "n/a"
		}
		infos = append(infos, PortInfo{Name: d.Name, Description: desc})
	}
	return infos, nil
}

// Open opens a serial port 8N1 at the given baud rate. go.bug.st/serial has
// no in_waiting equivalent and its reads block, so a background goroutine
// drains the OS buffer into an internal one that InWaiting()/Read() serve
// from without blocking — the semantics the polling loop expects.
func (SystemProvider) Open(name string, baudRate int) (Port, error) {
	mode := &serial.Mode{
		BaudRate: baudRate,
		DataBits: 8,
		Parity:   serial.NoParity,
		StopBits: serial.OneStopBit,
	}
	p, err := serial.Open(name, mode)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", name, err)
	}
	sp := &systemPort{port: p, open: true}
	go sp.pump()
	return sp, nil
}

type systemPort struct {
	port serial.Port

	mu   sync.Mutex
	buf  []byte
	err  error
	open bool
}

// pump moves bytes from the (blocking) OS port into the internal buffer.
func (s *systemPort) pump() {
	chunk := make([]byte, 4096)
	for {
		n, err := s.port.Read(chunk)
		s.mu.Lock()
		if n > 0 {
			s.buf = append(s.buf, chunk[:n]...)
		}
		if err != nil {
			if s.err == nil {
				s.err = err
			}
			s.open = false
			s.mu.Unlock()
			return
		}
		closed := !s.open
		s.mu.Unlock()
		if closed {
			return
		}
	}
}

func (s *systemPort) InWaiting() (int, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if len(s.buf) == 0 && s.err != nil {
		return 0, s.err
	}
	return len(s.buf), nil
}

func (s *systemPort) Read(p []byte) (int, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if len(s.buf) == 0 && s.err != nil {
		return 0, s.err
	}
	n := copy(p, s.buf)
	s.buf = s.buf[n:]
	return n, nil
}

func (s *systemPort) Write(p []byte) (int, error) {
	n, err := s.port.Write(p)
	if err != nil {
		s.mu.Lock()
		s.open = false
		s.mu.Unlock()
	}
	return n, err
}

func (s *systemPort) Close() error {
	s.mu.Lock()
	s.open = false
	s.mu.Unlock()
	return s.port.Close()
}

func (s *systemPort) IsOpen() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.open
}
