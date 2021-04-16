#!/bin/sh

sudo apt update
sudo apt install python3-pip python3-venv

# Point default symlinks to Python 3
sudo ln -sf /usr/bin/python3 /usr/bin/python
sudo ln -sf /usr/bin/pip3 /usr/bin/pip

# Additional OpenCV dependencies
sudo apt-get install libatlas-base-dev libhdf5-dev libhdf5-serial-dev libharfbuzz-dev libwebp-dev libtiff5 libjasper-dev libilmbase-dev libopenexr-dev libgstreamer1.0-dev libavcodec-dev libavformat-dev libgtk-3-0 libswscale-dev
