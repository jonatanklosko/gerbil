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
echo 3 > "${functions_dir}/report_length"
# Write the report descriptor
# Source: https://eleccelerator.com/tutorial-about-usb-hid-report-descriptors/
echo -ne "\x05\x01\x09\x02\xa1\x01\x09\x01\xa1\x00\x05\x09\x19\x01\x29\x03\x15\x00\x25\x01\x95\x03\x75\x01\x81\x02\x95\x01\x75\x05\x81\x03\x05\x01\x09\x30\x09\x31\x15\x81\x25\x7f\x75\x08\x95\x02\x81\x06\xc0\xc0" > "${functions_dir}/report_desc"

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
