# Gerbil

Simulating mouse device with Raspberry PI 4 and computer vision.

## Simulating mouse

```shell
# Run the initialization script. It's responsible for
# enabling necessary system modules and configuring the device.
# This needs to be executed just once and may require reboot.
sudo bin/initialize_device.sh

# Enable USB gadget representing our mouse HID.
sudo bin/enable_mouse_hid_gadget.sh

# Send Left Button Click (the first three bytes report
# the left button being pressed and the subsequent three bytes
# represent no buttons pressed).
echo -ne "\x01\x00\x00\x00\x00\x00" > /dev/hidg0
```

## Camera feed

To develop the image processing it's crucial to have access
to live camera feed (or already processed).

We first have to setup Python and all dependencies.

```shell
# Configure Python and install necessary system packages
bin/setup_python.sh

# Create venv for cleaner dependency management
python -m venv venv
source venv/bin/activate

# Install Python dependencies (notably OpenCV)
pip install -r requirements.txt
```

Now we can run the development server as follows:

```shell
FLASK_ENV=development FLASK_APP=src/dev_server.py flask run --host 0.0.0.0
```

This starts a web server on port `5000` and it should be accessible
at `http://raspberrypi.local:5000` in your local network.
If everything is set up correctly you should see live camera feed.

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
