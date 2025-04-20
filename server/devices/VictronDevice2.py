from .GenericSerialDevice import GenericSerialDevice
import time

class VictronDevice(GenericSerialDevice):
    def __init__(self, cache, portName):
        super(VictronDevice, self).__init__(cache, portName, 19200)
        self.statusVoltage = 0.0
        self.statusCurrent = 0.0
        self.statusPower = 0.0
        self.statusStateOfCharge = 0
        self.statusTimeRemaining = 0
        self.statusConsumedAh = 0.0
        self.block_buffer = bytearray()
        self.buffer = []

    def update(self):
        if self.open:
            try:
                # Read all available bytes
                data = self.port.read(self.port.in_waiting)
                self.block_buffer.extend(data)
                
                # Process blocks in the buffer
                while True:
                    # Look for the Checksum line
                    start_idx = self.block_buffer.find(b'\r\nChecksum\t')
                    if start_idx == -1:
                        break  # No complete block yet
                    
                    # Find the end of the Checksum line (ends with b'\r\n')
                    end_idx = self.block_buffer.find(b'\r\n', start_idx + 2)
                    if end_idx == -1:
                        break  # Incomplete Checksum line
                    end_idx += 2  # Include the CR LF
                    
                    # Extract the block from 0 to end_idx
                    block = self.block_buffer[:end_idx]
                    # Remove the processed block from the buffer
                    self.block_buffer = self.block_buffer[end_idx:]
                    
                    # Compute checksum
                    total = sum(block) % 256
                    if total != 0:
                        print("Checksum error")
                        continue
                    
                    # Parse the block
                    self.parse_block(block)
            except Exception as e:
                print(e)
                self.close()

    def parse_block(self, block):
        lines = block.split(b'\r\n')
        temp_data = {}
        for line in lines:
            if not line:
                continue
            parts = line.split(b'\t', 1)
            if len(parts) != 2:
                continue  # Invalid line
            label = parts[0].decode('ascii', errors='ignore')
            # Skip Checksum processing as it's already validated
            if label == 'Checksum':
                continue
            try:
                value = parts[1].decode('ascii')
                temp_data[label] = value
            except UnicodeDecodeError:
                continue  # Skip invalid values
        
        # Update variables with parsed data
        # print(temp_data)
        self.update_variables(temp_data)

    def update_variables(self, data):
        try:
            # Voltage (mV to V)
            if 'V' in data:
                self.statusVoltage = int(data['V']) / 1000.0
                self.cache.set("batteryVoltage", self.statusVoltage)
            
            # Current (mA to A)
            if 'I' in data:
                self.statusCurrent = int(data['I']) / 1000.0
                self.cache.set("batteryCurrent", self.statusCurrent)
            
            # Power (calculated as V * I)
            self.statusPower = self.statusVoltage * self.statusCurrent
            self.cache.set("batteryPower", self.statusPower)
            
            # State of Charge (%)
            if 'SOC' in data:
                self.statusStateOfCharge = int(data['SOC'])
                self.cache.set("batteryStateOfCharge", self.statusStateOfCharge / 10)
            
            # Time to Go (minutes)
            if 'TTG' in data:
                self.statusTimeRemaining = int(data['TTG'])
                self.cache.set("batteryTimeRemaining", self.statusTimeRemaining)
            
            # Consumed Amp Hours (mAh to Ah)
            if 'CE' in data:
                self.statusConsumedAh = int(data['CE']) / 1000.0
                self.cache.set("batteryConsumedAh", self.statusConsumedAh)
        
        except ValueError:
            # Handle non-integer values (e.g., '---')
            pass