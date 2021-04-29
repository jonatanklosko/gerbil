#!/bin/bash

# Creates USB Linux Gadget representing a mouse and binds it to UDC.
#
# After executing this script you can write bytes `/dev/hidg0`
# to simulate mouse device reports.
#
# References:
# - https://www.kernel.org/doc/Documentation/usb/gadget_configfs.txt
# - https://github.com/girst/hardpass-sendHID/blob/master/README.md
# - https://www.collabora.com/news-and-blog/blog/2019/02/18/modern-usb-gadget-on-linux-and-how-to-integrate-it-with-systemd-part-1
# - https://mtlynch.io/key-mime-pi

set -e

modprobe libcomposite

cd /sys/kernel/config/usb_gadget/
mkdir -p g1
cd g1

echo 0x1d6b > idVendor  # Linux Foundation
echo 0x0104 > idProduct # Multifunction Composite Gadget
echo 0x0100 > bcdDevice # v1.0.0
echo 0x0200 > bcdUSB    # USB2

strings_dir="strings/0x409" # 0x409 indicates English language
mkdir -p "$strings_dir"
echo "0" > "${strings_dir}/serialnumber"
echo "bendzo" > "${strings_dir}/manufacturer"
echo "Generic USB Mouse" > "${strings_dir}/product"

functions_dir="functions/hid.usb0"
mkdir -p "$functions_dir"
echo 2 > "${functions_dir}/protocol" # Mouse
echo 0 > "${functions_dir}/subclass" # No subclass
echo 5 > "${functions_dir}/report_length" # Set report length to 5 to match the device definition

# Write the report descriptor
#
# 0x05, 0x01,       // Usage Page (Generic Desktop)
# 0x09, 0x02,       // Usage (Mouse)
# 0xa1, 0x01,       // Collection (Application)
# 0x09, 0x01,       //   Usage (Pointer)
# 0xa1, 0x00,       //   Collection (Physical)
# 0x05, 0x09,       //     Usage Page (Buttons)
# 0x19, 0x01,       //     Usage Minimum (Button 1)
# 0x29, 0x03,       //     Usage Maximum (Button 3)
# 0x15, 0x00,       //     Logical Minimum (0)
# 0x25, 0x01,       //     Logical Maximum (1)
# 0x95, 0x03,       //     Report Count (3)
# 0x75, 0x01,       //     Report Size (1)
# 0x81, 0x02,       //     Input (Data, Variable, Absolute)
# 0x95, 0x01,       //     Report Count (1)
# 0x75, 0x05,       //     Report Size (5)
# 0x81, 0x03,       //     Input (Constant, Variable, Absolute)
# 0x05, 0x01,       //     Usage Page (Generic Desktop)
# 0x09, 0x30,       //     Usage (X)
# 0x09, 0x31,       //     Usage (Y)
# 0x15, 0x00,       //     Logical Minimum (0)
# 0x26, 0xff, 0x7f, //     Logical Maximum (32767)
# 0x75, 0x10,       //     Report Size (16)
# 0x95, 0x02,       //     Report Count (2)
# 0x81, 0x02,       //     Input (Data, Variable, Absolute)
# 0xc0,             //   End Collection
# 0xc0              // End Collection
#
echo -ne "\x05\x01\x09\x02\xa1\x01\x09\x01\xa1\x00\x05\x09\x19\x01\x29\x03\x15\x00\x25\x01\x95\x03\x75\x01\x81\x02\x95\x01\x75\x05\x81\x03\x05\x01\x09\x30\x09\x31\x15\x00\x26\xff\x7f\x75\x10\x95\x02\x81\x02\xc0\xc0" > "${functions_dir}/report_desc"

configs_dir="configs/c.1"
mkdir -p "$configs_dir"
echo 250 > "${configs_dir}/MaxPower"

configs_strings_dir="${configs_dir}/strings/0x409"
mkdir -p "$configs_strings_dir"
echo "No configuration required" > "${configs_strings_dir}/configuration"

ln -s "$functions_dir" "${configs_dir}"

# Bind gadget to UDC (USB Device Controller)
ls /sys/class/udc > UDC

chmod 777 /dev/hidg0
