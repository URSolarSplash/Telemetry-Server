package serialio

import (
	"errors"
	"sync"
)

// FakeProvider is an in-memory Provider for tests and hardware-free
// simulation. Ports can be plugged and unplugged at runtime to exercise the
// serial manager's scan/connect/disconnect logic.
type FakeProvider struct {
	mu    sync.Mutex
	ports map[string]*FakePort
	order []string
}

// NewFakeProvider returns an empty fake serial bus.
func NewFakeProvider() *FakeProvider {
	return &FakeProvider{ports: make(map[string]*FakePort)}
}

// Plug attaches a fake device to the bus and returns its port. The
// description plays the role of the USB product string used for device-type
// detection (e.g. "FT231X USB UART", "VE Direct cable", "ChibiOS/RT ...").
func (f *FakeProvider) Plug(name, description string) *FakePort {
	f.mu.Lock()
	defer f.mu.Unlock()
	port := &FakePort{name: name, description: description, open: true}
	if _, exists := f.ports[name]; !exists {
		f.order = append(f.order, name)
	}
	f.ports[name] = port
	return port
}

// Unplug removes a device from the bus, as if the USB cable were pulled.
func (f *FakeProvider) Unplug(name string) {
	f.mu.Lock()
	defer f.mu.Unlock()
	if port, ok := f.ports[name]; ok {
		port.failAll()
		delete(f.ports, name)
		for i, n := range f.order {
			if n == name {
				f.order = append(f.order[:i], f.order[i+1:]...)
				break
			}
		}
	}
}

// ListPorts returns the currently plugged ports in plug order.
func (f *FakeProvider) ListPorts() ([]PortInfo, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	infos := make([]PortInfo, 0, len(f.order))
	for _, name := range f.order {
		infos = append(infos, PortInfo{Name: name, Description: f.ports[name].description})
	}
	return infos, nil
}

// Open connects to a plugged port by name.
func (f *FakeProvider) Open(name string, baudRate int) (Port, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	port, ok := f.ports[name]
	if !ok {
		return nil, errors.New("no such port: " + name)
	}
	port.mu.Lock()
	port.baudRate = baudRate
	port.open = true
	port.mu.Unlock()
	return port, nil
}

// FakePort is an in-memory serial port. The test (playing the device) feeds
// bytes with FeedToServer and inspects what the server wrote with
// TakeWritten.
type FakePort struct {
	mu          sync.Mutex
	name        string
	description string
	baudRate    int
	open        bool
	failed      bool
	rx          []byte // bytes waiting for the server to read
	tx          []byte // bytes the server has written to the device
}

// FeedToServer queues bytes for the server to read, as if the device sent them.
func (p *FakePort) FeedToServer(b []byte) {
	p.mu.Lock()
	p.rx = append(p.rx, b...)
	p.mu.Unlock()
}

// TakeWritten returns and clears everything the server wrote to the device.
func (p *FakePort) TakeWritten() []byte {
	p.mu.Lock()
	defer p.mu.Unlock()
	out := p.tx
	p.tx = nil
	return out
}

// BaudRate reports the baud rate the server opened the port with.
func (p *FakePort) BaudRate() int {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.baudRate
}

// failAll makes every subsequent operation error, simulating an unplug.
func (p *FakePort) failAll() {
	p.mu.Lock()
	p.failed = true
	p.open = false
	p.mu.Unlock()
}

func (p *FakePort) InWaiting() (int, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.failed {
		return 0, errors.New("port unplugged")
	}
	return len(p.rx), nil
}

func (p *FakePort) Read(b []byte) (int, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.failed {
		return 0, errors.New("port unplugged")
	}
	n := copy(b, p.rx)
	p.rx = p.rx[n:]
	return n, nil
}

func (p *FakePort) Write(b []byte) (int, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.failed {
		return 0, errors.New("port unplugged")
	}
	p.tx = append(p.tx, b...)
	return len(b), nil
}

func (p *FakePort) Close() error {
	p.mu.Lock()
	p.open = false
	p.mu.Unlock()
	return nil
}

func (p *FakePort) IsOpen() bool {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.open && !p.failed
}
