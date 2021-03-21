#!/bin/bash

# Initializes the device by adding necessary kernel modules.

set -e

reboot_required=0

# Make sure we use the dwc2 USB driver.
# This driver is capable of handling OTG, consequently
# allowing this device to act as USB slave.

if ! grep "dtoverlay=dwc2" /boot/config.txt; then
  echo "dtoverlay=dwc2" >> /boot/config.txt
  reboot_required=1
fi

# Enable the corresponding kernel module.

if ! grep "dwc2" /etc/modules; then
  echo "dwc2" >> /etc/modules
  reboot_required=1
fi

if [ $reboot_required -eq 1 ]; then
  echo "Please reboot the device for the initialization to take effect"
else
  echo "Everything set up"
fi
