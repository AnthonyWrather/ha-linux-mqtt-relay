###############################################################################
#
# python -m pip install -r requirements.txt
#

import RPi.GPIO as GPIO            # import RPi.GPIO module
# from time import sleep             # lets us have a delay
import json
import logging
import random
import time
import re
import datetime as dt
from collections import defaultdict

from paho.mqtt import client as mqtt_client
from configparser import ConfigParser

###############################################################################
# Set up the config options.
config = ConfigParser(delimiters=('=', ))
config.read('config.ini')
###############################################################################

BROKER = config['mqtt'].get('broker', 'homeassistant.local')
PORT = int(config['mqtt'].get('port', '1883'))
# generate client ID with pub prefix randomly
CLIENT_ID = f'python-mqtt-tcp-pub-sub-{random.randint(0, 1000)}'
USERNAME = config['mqtt'].get('username', 'CONFIG_ME')
PASSWORD = config['mqtt'].get('password', 'CONFIG_ME')

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = int(config['mqtt'].get('timeout', '60'))
HOMEASSISTANT_STATUS_TOPIC = 'homeassistant/status'

all_devices = defaultdict(list)
devices = json.loads(config.get("homeassistant","device_names"))
for device in devices:
    TOPIC_BASE = config['homeassistant'].get('topic_base', 'default/homeassistant/switch')  \
        + '/relay/' + device + '/'

    devices_config = {
        "topic_config": TOPIC_BASE + config['mqtt'].get('topic_config', 'config'),
        "topic_set": TOPIC_BASE + config['mqtt'].get('topic_set', 'set'),
        "topic_state": TOPIC_BASE + config['mqtt'].get('topic_state', 'state'),
        "topic_availability": TOPIC_BASE + config['mqtt'].get('topic_availability', 'availability'),
        "pin": 0
    }
    all_devices[device].append(devices_config)

RELAY_CONFIG_PAYLOAD = {
  "device_class":"switch",
  "name": "",
  "unique_id": "",
  "state_topic": "",
  "command_topic": "",
  "availability_topic": "",
  "value_template":"{{value_json.switch}}",
  "optimistic": "false",
  "qos": "0",
  "retain": "true",
  "device": {
    "identifiers": ["linux_switches"],
    "name": "Switches",
    "manufacturer": "Example Sensors Ltd.",
    "model": "Example Relay",
    "model_id": "On-Off-Switch",
    "hw_version": "Linux-0.01a",
    "sw_version": "2026.4.0",
    "configuration_url": "https://github.com/AnthonyWrather/ha-linux-mqtt-relay"
  }
}

RELAY_ADDITIONAL_CONFIG_PAYLOAD = {
  "device_class":"switch",
  "name": "",
  "unique_id": "",
  "state_topic": "",
  "command_topic": "",
  "availability_topic": "",
  "value_template":"{{value_json.switch}}",
  "optimistic": "false",
  "qos": "0",
  "retain": "true",
  "device": {
    "identifiers": ["linux_switches"],
  }
}

###############################################################################

def on_connect(client, userdata, flags, rc, properties=None):
    logging.info(f"Reached: On Connect with result code {rc}")
    setup_device(rc, client)


def setup_device(rc, client):
    logging.info("Reached: Setup Device.")
    # Send the config and enable everything.
    if rc == 0 and client.is_connected():
        logging.info("Connected to MQTT Broker!")
        count = 0
        for device, data in all_devices.items():
            # Publish the Device config for auto discovery.
            logging.info("===================================================================")
            logging.info(f"Processing device {device}")
            if count == 0:
                # Set the primary payload.
                logging.info(f"State topic: {data[0]['topic_state']}")
                logging.info(f"Command topic: {data[0]['topic_set']}")
                logging.info(f"Availability topic: {data[0]['topic_availability']}")
                RELAY_CONFIG_PAYLOAD["name"] = device
                RELAY_CONFIG_PAYLOAD["unique_id"] = device
                RELAY_CONFIG_PAYLOAD["state_topic"] = data[0]['topic_state']
                RELAY_CONFIG_PAYLOAD["command_topic"] = data[0]['topic_set']
                RELAY_CONFIG_PAYLOAD["availability_topic"] = data[0]['topic_availability']
                msg = json.dumps(RELAY_CONFIG_PAYLOAD)
                count += 1
            else:
                # Set the additional payload.
                logging.info(f"Processing additional device {device}")
                logging.info(f"State topic: {data[0]['topic_state']}")
                logging.info(f"Command topic: {data[0]['topic_set']}")
                logging.info(f"Availability topic: {data[0]['topic_availability']}")
                RELAY_ADDITIONAL_CONFIG_PAYLOAD["name"] = device
                RELAY_ADDITIONAL_CONFIG_PAYLOAD["unique_id"] = device
                RELAY_ADDITIONAL_CONFIG_PAYLOAD["state_topic"] = data[0]['topic_state']
                RELAY_ADDITIONAL_CONFIG_PAYLOAD["command_topic"] = data[0]['topic_set']
                RELAY_ADDITIONAL_CONFIG_PAYLOAD["availability_topic"] = data[0]['topic_availability']
                msg = json.dumps(RELAY_ADDITIONAL_CONFIG_PAYLOAD)
                count += 1

            logging.info(f"Sending Config Message = {msg}")
            result = client.publish(data[0]['topic_config'], msg)
            status = result[0]
            if status != 0:
                logging.info(f'Failed to send SWITCH config to topic {data[0]['topic_config']}')
            else:
                logging.info(f'Successfully sent SWITCH config to topic {data[0]['topic_config']}')
            # Publish the availability - ONLINE
            time.sleep(0.5)
            result = client.publish(data[0]['topic_availability'], 'online')
            status = result[0]
            if status != 0:
                logging.info(f'Failed to set availability to online for topic {data[0]['topic_availability']}')
            else:
                logging.info(f'Successfully set availability to online for topic {data[0]['topic_availability']}')
            logging.info(f'Subscribing to topic {data[0]['topic_set']}')
            client.subscribe(data[0]['topic_set'])
            logging.info(f'Subscribing to topic {HOMEASSISTANT_STATUS_TOPIC}')
            client.subscribe(HOMEASSISTANT_STATUS_TOPIC)
            time.sleep(0.5)
            set_state(client, device)
        logging.info('===================================================================')
        logging.info('Successfully finished device setup.')
    else:
        logging.info(f'Failed to connect, return code {rc}')


def on_disconnect(client, userdata, flags, rc, properties):
    logging.info("Reached: Disconnected with result code: %s", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info("Reconnecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logging.info("Reconnected successfully!")
            for device in all_devices:
              logging.info(f"Setting device {device} to ONLINE")
              result = client.publish(all_devices[device][0]['topic_availability'], 'online')
              status = result[0]
              if status != 0:
                  logging.info(f'Failed to set availability to online for topic {all_devices[device][0]['topic_availability']}')
              else:
                  logging.info(f'Successfully set availability to online for topic {all_devices[device][0]['topic_availability']}')
            # If there are any scenarios where I need to resubscribe here is the place to do it.
            return
        except Exception as err:
            logging.error("%s. Reconnect failed. Retrying...", err)

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1

    logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)


def on_message(client, userdata, msg):
    logging.info('==================================================================')
    logging.info(f'Reached: On Message `{msg.payload.decode()}` from `{msg.topic}` topic')
    match msg.topic:
        # case str(HOMEASSISTANT_STATUS_TOPIC):
        case str('homeassistant/status'):
            logging.info(f"Received message on {msg.topic} topic: {msg.payload.decode()}")
            match msg.payload.decode():
                case 'online':
                    if client is not None and client.is_connected():
                        logging.info("Client is already connected, need to disconnect.")
                        # client.disconnect()
                        # client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, CLIENT_ID)
                        client.reconnect()
                    else:
                        logging.info("Client is not connected.")
                    setup_device(0, client)
                    return

                case 'offline':
                    # Could switch off the device?
                    return
                case _:
                    logging.info(f'Received UNKNOWN payload: {msg.payload.decode()}')
                    return
        case _:
            # now its regex time...
            pattern = r"(?<=/)[^/\n]+(?=/[^/\n]*$)"
            device = (re.search(pattern, msg.topic)).group(0)
            logging.info(f"Using device {device}")
            match msg.payload.decode():
                case 'ON':
                    # Set state to ON
                    logging.info(f'Received payload: {msg.payload.decode()}')
                    set_state(client, device, 'ON')
                    return
                case 'OFF':
                    # Set state to off
                    logging.info(f'Received payload: {msg.payload.decode()}')
                    set_state(client, device, 'OFF')
                    return
                case _:
                    logging.info(f'Received UNKNOWN payload: {msg.payload.decode()}')
                    return


def connect_mqtt():
    logging.info("Reached: Connect MQTT")
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info("Connecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)
        try:
            client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, CLIENT_ID)
            client.username_pw_set(USERNAME, PASSWORD)
            client.on_connect = on_connect
            client.on_message = on_message
            logging.info(f"Reached connect_mqtt 4")
            error = client.connect(BROKER, PORT, keepalive=120)
            logging.info(f"Reached connect_mqtt 5")
            client.on_disconnect = on_disconnect
            logging.info(f"Reached connect_mqtt 6")
            logging.info(f"connect_mqtt: {client}")
            return client
        except Exception as err:
            logging.error("%s. Connection failed...", err)
        except:
            # this catches ALL other exceptions including errors.
            # You won't get any error messages for debugging
            # so only use it once your code is working
            logging.info( "A general connection exception occurred!" )
        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1


def publish(client, topic, payload):
    logging.info('==================================================================')
    msg = json.dumps(payload)
    logging.info(f'Reached: Publish Message `{msg}` to `{topic}` topic')
    if not client.is_connected():
        logging.error("publish: MQTT client is not connected!")
        time.sleep(1)
    result = client.publish(topic, msg)
    status = result[0]
    if status == 0:
        logging.info(f'Send `{msg}` to topic `{topic}`')
    else:
        logging.info(f'Failed to send message to topic {topic}')
    time.sleep(1)


def set_state(client, device, state=None):
    # Need to set the device config to use.
    logging.info("Set State")
    state_topic = all_devices[device][0]['topic_state']
    device_pin = all_devices[device][0]['pin']
    if state == None:
        logging.info(f'set_state: No state provided, using current state of pin {device_pin}')
        if get_relay(all_devices[device][0]['pin']):
            state = 'ON'
        else:
            state = 'OFF'
    # Get the state of the pin
    old_state = get_relay(device_pin)
    if old_state:
        old_state = "ON"
    else:
        old_state =  "OFF"
    logging.info(f'Initial pin ({device_pin}) state is {old_state} and the desired state is {state}')
    match state:
        case 'ON':
          logging.info("Received ON Command.")
          if state != old_state:
              # set pin state
              logging.info(f"Set pin {device_pin} to sate {state}")
              set_relay(device_pin, GPIO.HIGH)
          # publish new state
          logging.info(f"Set state {state_topic} to sate ON")
          result = client.publish(state_topic, 'ON')
          return
        case 'OFF':
          logging.info("Received OFF command.")
          if state != old_state:
              # set pin state
              logging.info(f"Set pin {device_pin} to sate {state}")
              set_relay(device_pin, GPIO.LOW)
          # publish new state
          logging.info(f"Set state {state_topic} to sate OFF")
          result = client.publish(state_topic, 'OFF')
          return
        case _:
          logging.info(f'set_state: Received unknown state: {state}')
          return


def set_relay( pin, state ):
    GPIO.output(pin, state)


def get_relay(pin):
    return GPIO.input(pin)


###############################################################################
def run():
    try:
        # Main loop goes here.
        logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s',
                            level=logging.DEBUG)
        client = connect_mqtt()
        client.loop_forever()

    except KeyboardInterrupt:
        # here you put any code you want to run before the program
        # exits when you press CTRL+C
        logging.info( "Keyboard interrupt\n" )

    # except:
    #     # this catches ALL other exceptions including errors.
    #     # You won't get any error messages for debugging
    #     # so only use it once your code is working
    #     logging.info( "A general exception occurred!" )

    finally:
        logging.info(f'Reached Finally!')
        # this ensures a clean GPIO exit
        GPIO.cleanup()
        if client is not None and client.is_connected():
          # RELAY_CONFIG_PAYLOAD["availability_topic"] = data[0]['topic_availability']
          for device, data in all_devices.items():
              result = client.publish(data[0]['topic_availability'], 'offline')
              status = result[0]
              if status != 0:
                  logging.info(f'Failed to set availability to OFFLINE for topic {data[0]['topic_availability']}')
              else:
                  logging.info(f'Successfully set availability to OFFLINE for topic {data[0]['topic_availability']}')


if __name__ == '__main__':
    GPIO.setmode(GPIO.BCM)             # choose BCM or BOARD
    # Get the pins
    pins = json.loads(config.get("sensor","pins"))
    count = 0
    # Set the pins in the main struct
    for device in all_devices:
        all_devices[device][0]['pin'] = pins[count]
        GPIO.setup(all_devices[device][0]['pin'], GPIO.OUT)
        count += 1
    run()
