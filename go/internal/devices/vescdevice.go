package devices

import (
	"fmt"

	"telemetryserver/internal/data"
	"telemetryserver/internal/serialio"
	"telemetryserver/internal/vesc"
)

// VescDevice talks to a VESC motor controller (port of VescDevice.py): it
// periodically writes the throttle command and polls COMM_GET_VALUES.
type VescDevice struct {
	*GenericSerialDevice
	lastWrite float64
	writeRate float64 // seconds
}

func NewVescDevice(provider serialio.Provider, cache *data.DataCache, portName string) *VescDevice {
	return &VescDevice{
		GenericSerialDevice: NewGenericSerialDevice(provider, cache, portName, 115200),
		lastWrite:           data.Now(),
		writeRate:           0.1,
	}
}

func (d *VescDevice) Update() {
	if !d.open {
		return
	}
	if data.Now()-d.lastWrite > d.writeRate {
		d.lastWrite = data.Now()
		if err := d.writeData(); err != nil {
			fmt.Println(err)
			d.Close()
			return
		}
	}
	waiting, err := d.port.InWaiting()
	if err != nil {
		fmt.Println(err)
		d.Close()
		return
	}
	if waiting >= 71 {
		// Check for a new vesc message in the buffer
		chunk := make([]byte, 70)
		n, err := d.port.Read(chunk)
		if err != nil {
			fmt.Println(err)
			d.Close()
			return
		}
		values, err := vesc.DecodeValues(chunk[:n])
		if err != nil {
			return // no valid GetValues frame in this chunk
		}
		d.cache.Set("boatConfig", 0)
		d.cache.Set("motorTemp", values.TempMotorFiltered)
		d.cache.Set("controllerTemp", values.TempFetFiltered)
		d.cache.Set("controllerInCurrent", values.AvgInputCurrent)
		d.cache.Set("controllerOutCurrent", values.AvgMotorCurrent)
		d.cache.Set("controllerDutyCycle", values.DutyCycle)
		d.cache.Set("controllerRpm", values.Rpm)
		d.cache.Set("controllerInVoltage", values.VIn)
	}
}

// writeData gets the throttle value and writes it to the vesc, then requests
// fresh values.
//   - Throttle duty cycle value range for vesc: -100,000 to 100,000
//   - Input throttle: 0 to 255
//   - Only write a throttle value if we are in endurance mode (boatConfig 0)
func (d *VescDevice) writeData() error {
	if d.cache.GetNumerical("boatConfig", 0) == 0 {
		if d.cache.GetNumerical("throttleMode", 0) == 0 {
			throttle := (d.cache.GetNumerical("throttle", 0) / 255.0) * 100.0 * 1000.0
			if _, err := d.port.Write(vesc.EncodeSetDutyCycle(int32(throttle))); err != nil {
				return err
			}
		} else {
			// Goal current is the MOTOR CURRENT; to convert from battery
			// current: MOTOR CURRENT = BATTERY CURRENT / DUTY CYCLE
			batteryCurrent := d.cache.GetNumerical("throttleCurrentTarget", 0)
			dutyCycle := d.cache.GetNumerical("controllerDutyCycle", 0) / 10.0
			motorCurrent := 0.0
			if dutyCycle > 0 {
				motorCurrent = (batteryCurrent / dutyCycle) * -1.0 * 1000.0
			}
			if _, err := d.port.Write(vesc.EncodeSetCurrent(int32(motorCurrent))); err != nil {
				return err
			}
		}
	} else {
		if _, err := d.port.Write(vesc.EncodeSetDutyCycle(0)); err != nil {
			return err
		}
	}
	_, err := d.port.Write(vesc.EncodeGetValuesRequest())
	return err
}
