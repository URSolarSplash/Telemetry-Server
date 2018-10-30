echo "SOLAR SPLASH BOOT LOADER"
echo "Starting up..."

echo "Mounting USB disk..."
sudo mount -t hfsplus -o uid=pi,gid=pi /dev/sda1 /mnt/usb
echo "Mounted USB disk!"

echo "Running mounted disk bootloader..."
/mnt/usb/run.sh
