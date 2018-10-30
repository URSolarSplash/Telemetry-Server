# Mounted bootloader script

echo "Starting Telemetry Server..."

# Make sure we're in the right directory
cd /mnt/usb/

# Run python telemetry server program
python main.py
