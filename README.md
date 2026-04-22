# ha-linux-mqtt-relay
A Python service to automatically create a Linux device to control a relay in Home Assistant via MQTT.<BR>
Should work with any Raspberry Pi compatible relay device.<BR>
To get started download this repository, edit the **config.ini** file and start a screen session.<BR>
This assumes you already have **Python 3** and **screen** installed.<BR>


## Initial Setup

Download the repo from GitHub and change into the new directory.

``` bash
git clone https://github.com/AnthonyWrather/ha-linux-mqtt-relay.git
cd ha-linux-mqtt-relay
```

Create the venv and install the requirements.

``` bash
python -m venv .ha-linux-mqtt-relay
source .ha-linux-mqtt-relay/bin/activate
pip install -r requirements.txt
```

If you don't have a ~/bin directory create one and optionally add it to your path.<BR>
In ~/bin create ha-linux-mqtt-relay.sh

``` bash
#!/bin/bash
cd /home/controlpi/Projects/adafruit/ha-linux-mqtt-relay
source .ha-linux-mqtt-relay/bin/activate
while true; do python ha-linux-mqtt-relay.py; done;
deactivate
```
## Edit config.ini

In this example you have

* A Home Assistant server called **homeassistant.lan** with a user called **controlpi_mqtt** with a password of **CHANGE_ME**
* The Home Assistant server has MQTT installed and running with the default **homeassistant** base.
* A Raspberry Pi called **controlpi.lan** with a user called **controlpi** with a password of **CHANGE_ME**
* On **controlpi.lan** there is a relay connected to PIN 23 which controls a fan.

``` conf
[mqtt]

broker = homeassistant.lan
username = controlpi_mqtt
password = CHANGE_ME
port = 1883
timeout = 60

[sensor]

pin = 23
type = dht11
interval = 60
decimal_digits = 4

[homeassistant]

device_name = /fan
topic_base = homeassistant/switch
topic_config = /conf
topic_state = /state
topic_set = /set
topic_availability = /availability
```

## Quick Start

To run this from the command line.

``` bash
screen -dmS ha-linux-mqtt-relay
screen -S ha-linux-mqtt-relay -p 0 -X '~/bin/ha-linux-mqtt-relay.sh\n'
```


## Install as a service.

Follow the Initial Setup steps then create the service.

``` bash
sudo systemctl edit --force --full ha-linux-mqtt-relay.service
sudo systemctl edit ha-linux-mqtt-relay.service
```

Place the following into the service.

``` conf
[Unit]
Description=ha-linux-mqtt-relay daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=idle
User=controlpi
Group=controlpi
WorkingDirectory=/home/controlpi
ExecStart=/home/controlpi/bin/ha-linux-mqtt-relay.sh
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=1
TimeoutStartSec=10
TimeoutStopSec=10
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/games:/usr/games"

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ha-linux-mqtt-relay

[Install]
WantedBy=multi-user.target
```

And you can use the following to enable and check on the service.

``` bash
sudo systemctl enable ha-linux-mqtt-relay.service
sudo systemctl status ha-linux-mqtt-relay.service
sudo systemctl start ha-linux-mqtt-relay.service
sudo systemctl restart ha-linux-mqtt-relay.service
```

