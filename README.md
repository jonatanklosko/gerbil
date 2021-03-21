# Gerbil

Simulating mouse device with Raspberry PI 4 and computer vision.

## Simulating mouse

```shell
# Run the initialization script. It's responsible for
# enabling necessary system modules and configuring the device.
# This needs to be executed just once and may require reboot.
bin/initialize_device.sh

# Enable USB gadget representing our mouse HID.
bin/enable_mouse_hid_gadget.sh

# Send Left Button Click (the first three bytes report
# the left button being pressed and the subsequent three bytes
# represent no buttons pressed).
echo -ne "\x01\x00\x00\x00\x00\x00" > /dev/hidg0
```
