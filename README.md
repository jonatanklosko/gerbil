# Gerbil

Simulating mouse device with Raspberry Pi 4 and computer vision.

https://user-images.githubusercontent.com/17034772/118178788-bb621b00-b434-11eb-99e6-d3dccc9be206.mp4

## Setup

First, initialize the device and install the all necessary dependencies.

```sh
# Run the initialization script. It's responsible for
# enabling necessary system modules and configuring the device.
# This needs to be executed just once and may require reboot.
sudo bin/initialize_device.sh

# Configure Python and install necessary system packages
sudo bin/setup_python.sh

# Create venv for cleaner dependency management
python -m venv venv
source venv/bin/activate

# Install Python dependencies (notably OpenCV)
pip install -r requirements.txt
```

Then start the application.

```sh
# Enable USB gadget representing our mouse HID
sudo bin/enable_mouse_hid_gadget.sh

# Start analyzing video and interpreting it as mouse movement
python src/main.py
```

## Development

To develop the image processing it's crucial to have access
to live camera feed (or already processed). To do so, you
can run the development server as follows (still on the device):

```sh
FLASK_ENV=development FLASK_APP=src/dev_server.py flask run --host 0.0.0.0
```

This starts a web server on port `5000` and it should be accessible
at `http://raspberrypi.local:5000` in your local network.
If everything is set up correctly you should see live camera feed.

## How it works

Generally USB devices like mouse or keyboard fall under a broad
HID (Human Interface Device) category. Such devices send standardized
messages over USB to the host (usually your computer).
Linux provides USB Gadget API that allows the system to simulate
a HID device and send the standardized messages.
For that to work, the device at hand must be able to work in USB device
mode, which Raspberry Pi 4 does.

Putting the video-processing application aside, to simulate a mouse click
all you need to do is create the virtual device using Linux Gadget API,
and then start sending bytes over USB using Linux device-file abstraction:

```sh
# Enable USB gadget representing our mouse HID.
sudo bin/enable_mouse_hid_gadget.sh

# Send Left Button Click (the first five bytes report
# the left button being pressed and the subsequent five bytes
# represent no buttons pressed).
echo -ne "\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00" > /dev/hidg0
```

Gerbil builds on top of this idea, by analyzing feed from camera
and sending such byte sequences to move cursor around
matching how the hand moves within camera view.

## Notes

OpenCV is distributed with Python Wheels, so when the package
is fetched with already pre-built native modules.
However, in our case installing the latest versions of OpenCV failed to
fetch the cached build and resulted in building everything from source.
Building from source may take up to several hours on Raspberry PI,
so that's far from a seamless experience. Fortunately pinning OpenCV
package to an older version (namely `4.1.0.25`) did help and made the installation quick.

Also there is a significant amount of system packages required
in order to satisfy OpenCV runtime dependencies (i.e. dynamic libraries).
We empirically gathered the necessary libraries and they are installed
as part of the `bin/setup_python.sh` script.
