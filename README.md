# ha-linux-mqtt-relay

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Dependabot Status](https://img.shields.io/badge/Dependabot-enabled-025e8c?logo=dependabot)](https://dependabot.com)
[![GitHub repo](https://img.shields.io/badge/github-repo-000)](https://github.com/AnthonyWrather/ha-linux-mqtt-relay)

A Python service that automatically creates a Linux device in Home Assistant to control a relay via MQTT. This project enables seamless integration of GPIO-controlled relays with Home Assistant using the MQTT Discovery protocol.

This has been tested on the following hardware with generic 5V relays.

- Raspberry Pi 2B running Trixie
- Raspberry Pi 3B running Buster
- Raspberry Pi 5B running Trixie

Other versions of Linux should also work so long as they run Python 3.X

## Features

- **GPIO Relay Control**: Control GPIO-connected relays from Home Assistant
- **MQTT Discovery**: Automatic device discovery in Home Assistant (no manual configuration needed)
- **Auto-Reconnection**: Robust MQTT reconnection handling with exponential backoff
- **Availability Tracking**: Reports online/offline status to Home Assistant
- **Configurable**: Fully configurable via `config.ini` (broker, credentials, GPIO pins, topics)
- **Service Support**: Can run as a systemd service for persistent operation

## Prerequisites

- Raspberry Pi or compatible Linux device with GPIO support
- Python 3.7+
- MQTT broker (e.g., Home Assistant with MQTT addon, Mosquitto)
- Relay module connected to a GPIO pin
- GPIO libraries support (e.g., RPi.GPIO)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/AnthonyWrather/ha-linux-mqtt-relay.git
cd ha-linux-mqtt-relay
```

### 2. Create Python Virtual Environment

```bash
python -m venv .ha-linux-mqtt-relay
source .ha-linux-mqtt-relay/bin/activate
pip install -r requirements.txt
```

### 3. Create Helper Script

Create `~/bin/ha-linux-mqtt-relay.sh` (create the `~/bin` directory if it doesn't exist):

```bash
#!/bin/bash
cd "$(dirname "$0")/../Projects/adafruit/ha-linux-mqtt-relay" || exit
source .ha-linux-mqtt-relay/bin/activate
while true; do python ha-linux-mqtt-relay.py; done
deactivate
```

Make it executable:

```bash
chmod +x ~/bin/ha-linux-mqtt-relay.sh
```
## Configuration

Copy `config.ini.EXAMPLE` to `config.ini` and update the following settings:

```bash
cp config.ini.EXAMPLE config.ini
nano config.ini
```

### Configuration Parameters

#### [mqtt] Section

```conf
[mqtt]
broker = homeassistant.lan          # MQTT broker hostname or IP
username = mqtt_user                # MQTT username
password = your_secure_password     # MQTT password
port = 1883                         # MQTT port (default: 1883)
timeout = 60                        # Reconnection timeout in seconds
topic_config = /config              # MQTT discovery config topic suffix
topic_state = /state                # State publication topic suffix
topic_set = /set                    # Command subscription topic suffix
topic_availability = /availability  # Availability status topic suffix
```

#### [sensor] Section

```conf
[sensor]
pin = 23                 # GPIO pin number (BCM numbering)
interval = 60            # Update interval in seconds
```

#### [homeassistant] Section

```conf
[homeassistant]
device_name = /fan              # Device identifier (used in MQTT topics)
topic_base = homeassistant/switch  # Base topic for MQTT discovery
```

### Example Configuration

Here's a typical setup example:

```conf
[mqtt]
broker = homeassistant.local
username = controlpi_mqtt
password = CHANGE_ME
port = 1883
timeout = 60

[sensor]
pin = 23
interval = 60

[homeassistant]
device_name = /fan
topic_base = homeassistant/switch
topic_config = /config
topic_state = /state
topic_set = /set
topic_availability = /availability
```

## Running the Service

### Option 1: Manual Execution (Development/Testing)

```bash
# Activate the virtual environment
source .ha-linux-mqtt-relay/bin/activate

# Run the script
python ha-linux-mqtt-relay.py
```

### Option 2: Screen Session

```bash
# Start a detached screen session
screen -dmS ha-linux-mqtt-relay ~/bin/ha-linux-mqtt-relay.sh

# View logs
screen -S ha-linux-mqtt-relay -X hardcopy -h -S - | tail -50

# Attach to the session
screen -r ha-linux-mqtt-relay

# Detach from the session (press Ctrl+A, then D)
```

### Option 3: Systemd Service (Recommended for Production)

#### Create the Service File

```bash
sudo systemctl edit --force --full ha-linux-mqtt-relay.service
```

Paste the following configuration:

```ini
[Unit]
Description=ha-linux-mqtt-relay MQTT Relay Control Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=controlpi
Group=controlpi
WorkingDirectory=/home/controlpi/Projects/adafruit/ha-linux-mqtt-relay
ExecStart=/home/controlpi/bin/ha-linux-mqtt-relay.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ha-linux-mqtt-relay

[Install]
WantedBy=multi-user.target
```

#### Enable and Start the Service

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable ha-linux-mqtt-relay.service

# Start the service
sudo systemctl start ha-linux-mqtt-relay.service

# Check service status
sudo systemctl status ha-linux-mqtt-relay.service

# View service logs
journalctl -u ha-linux-mqtt-relay.service -f
```

## Home Assistant Integration

Once the service is running, Home Assistant will automatically discover the relay device via MQTT Discovery. The device will appear in Home Assistant's integrations without any manual configuration needed.

### MQTT Topics

The service publishes to the following MQTT topics:

- **Config Topic**: Used for Home Assistant auto-discovery (sends device configuration)
- **State Topic**: Publishes the current relay state (`ON` or `OFF`)
- **Set Topic**: Subscribes to commands to change the relay state
- **Availability Topic**: Publishes availability status (`online` or `offline`)

All topics are dynamically generated based on `config.ini` settings:

```
{topic_base}/relay{device_name}/{topic_config}
{topic_base}/relay{device_name}/{topic_state}
{topic_base}/relay{device_name}/{topic_set}
{topic_base}/relay{device_name}/{topic_availability}
```

## Troubleshooting

### Service Won't Start

Check the service logs:

```bash
journalctl -u ha-linux-mqtt-relay.service -n 50 -e
```

### MQTT Connection Issues

1. **Verify MQTT Broker**: Check that your MQTT broker is running and accessible
   ```bash
   # Test connection from your device
   mosquitto_sub -h homeassistant.local -u mqtt_user -P your_password -t '#'
   ```

2. **Check Credentials**: Ensure username and password in `config.ini` are correct

3. **Verify Broker Address**: Ensure `config.ini` has the correct broker hostname/IP

### GPIO Issues

1. **Check GPIO Pin Number**: Verify the pin number in `config.ini` matches your relay's GPIO pin
2. **Check Permissions**: Ensure the user running the service has GPIO permissions
3. **GPIO Already in Use**: Check if another process is using the same GPIO pin

### Device Not Appearing in Home Assistant

1. Check that MQTT integration is enabled in Home Assistant
2. Verify the service is running: `systemctl status ha-linux-mqtt-relay.service`
3. Check the device availability topic for `online` status
4. Check Home Assistant logs for MQTT-related errors

### Debugging

To see detailed debug output:

```bash
# Run the script directly (not as a service)
source .ha-linux-mqtt-relay/bin/activate
python ha-linux-mqtt-relay.py
```

This will display logging output to the console for troubleshooting.

## Development Notes

- The code uses Python 3 with the `paho-mqtt` library for MQTT communication
- GPIO control is handled by `RPi.GPIO` library
- Configuration is read from `config.ini` using Python's `configparser`
- The service maintains automatic reconnection to the MQTT broker with exponential backoff
- Home Assistant discovery is done via the MQTT Discovery protocol

## Resources

- [Home Assistant MQTT Documentation](https://www.home-assistant.io/integrations/mqtt/)
- [Home Assistant MQTT Discovery](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery)
- [Paho MQTT Python Client](https://github.com/eclipse/paho.mqtt.python)
- [RPi.GPIO Documentation](https://sourceforge.net/p/raspberry-gpio-python/wiki/Home/)

## License

See [LICENSE](LICENSE) file for details.

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community guidelines.

