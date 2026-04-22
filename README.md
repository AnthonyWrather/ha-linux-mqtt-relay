# ha-linux-mqtt-relay
A Python service to automatically create a Linux device to control a relay in Home Assistant via MQTT.

=============================================

In bin create ha-linux-mqtt-relay.sh

``` sh
#!/bin/bash
cd /home/controlpi/Projects/adafruit/ha-linux-mqtt-relay
source .ha-linux-mqtt-relay/bin/activate
while true; do python ha-linux-mqtt-relay.py; done;
deactivate
```

Then run
``` bash
screen -dmS ha-linux-mqtt-relay
screen -S ha-linux-mqtt-relay -p 0 -X 'ha-linux-mqtt-relay.sh\n'
```
=============================================
