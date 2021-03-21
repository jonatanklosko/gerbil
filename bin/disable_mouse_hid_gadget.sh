#!/bin/bash

# Effectively reverses `enable_mouse_hid_gadget.sh`
# by removing the gadget specification.
#
# Reference: https://www.kernel.org/doc/Documentation/usb/gadget_configfs.txt

set -e

cd /sys/kernel/config/usb_gadget/g1

echo "" > UDC

# Remove the symlink
rm configs/c.1/hid.usb0

rmdir configs/c.1/strings/0x409
rmdir configs/c.1
rmdir functions/hid.usb0
rmdir strings/0x409

cd ..
rmdir g1
