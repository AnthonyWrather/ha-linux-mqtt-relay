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

from paho.mqtt import client as mqtt_client
from configparser import ConfigParser

###############################################################################
# Set up the config options.
config = ConfigParser(delimiters=('=', ))
config.read('config.ini')

sensor_type = config['sensor'].get('type', 'dht22').lower()

###############################################################################

BROKER = config['mqtt'].get('hostname', 'homeassistant.local').lower()
PORT = config['mqtt'].get('port', '1883').lower()
# generate client ID with pub prefix randomly
CLIENT_ID = f'python-mqtt-tcp-pub-sub-{random.randint(0, 1000)}'
USERNAME = config['mqtt'].get('username', 'CONFIG_ME').lower()
PASSWORD = config['mqtt'].get('password', 'CONFIG_ME').lower()

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = config['mqtt'].get('timeout', '60').lower()

# Define the main device and a single sensor.
# Publish here to create or update the device.
# TODO: Add in device name to topics and names.
TOPIC_BASE = config['mqtt'].get('topic_base', 'homeassistant/switch').lower() + config['mqtt'].get('device_name', '/relay').lower()
TOPIC_MAINCABIN_FAN_CONFIG = TOPIC_BASE + config['mqtt'].get('topic_config', '/config').lower()

# Update Payload to ON/OFF
# Set to the current state of the fan ON/OFF.
# Publish here to broadcast the current state of the device.
TOPIC_MAINCABIN_FAN_STATE = TOPIC_BASE + config['mqtt'].get('topic_state', '/state').lower()
TOPIC_MAINCABIN_FAN_STATE_EXAMPLE = {
  'on'
}

# Command Payload  ON/OFF
# Recive a command to set the fan ON/OFF.
# Subscribe here to get commands.
TOPIC_MAINCABIN_FAN_SET = TOPIC_BASE + config['mqtt'].get('topic_set', '/set').lower()
TOPIC_MAINCABIN_FAN_SET_EXAMPLE = {
  'on'
}


# availlability Payload  ONLINE/OFFLINE
# Set to ONLINE on start and OFFLINE on exit.
# Publish here to say this device is available.
TOPIC_MAINCABIN_FAN_AVAILLABILTY = TOPIC_BASE + config['mqtt'].get('topic_availability', '/availability').lower()
TOPIC_MAINCABIN_FAN_AVAILLABILTY_EXAMPLE = {
  'online'
}

TOPIC_MAINCABIN_FAN_CONFIG_PAYLOAD = {
  "device_class":"switch",
  "name": "Fan 01",
  "state_topic": TOPIC_MAINCABIN_FAN_STATE,
  "command_topic": TOPIC_MAINCABIN_FAN_SET,
  "availability_topic": TOPIC_MAINCABIN_FAN_AVAILLABILTY,
  "value_template":"{{value_json.switch}}",
  "optimistic": "false",
  "qos": "0",
  "unique_id":"mcfan01ae",
  "retain": "true",
  "unique_id": "maincabin_fan_01",
  "device": {
    "identifiers": ["maincabin_fan_01"],
    "name": "Main Cabin Fan",
    "manufacturer": "Example Sensors Ltd.",
    "model": "Example Sensor",
    "model_id": "Relay Fan",
    "hw_version": "0.01a",
    "sw_version": "2026.4.0",
    "configuration_url": "https://github.com/AnthonyWrather/ha-linux-mqtt-relay"
  }
}


# These will move to a config file.
pin = config['sensor'].get('pin', '23').lower()


GPIO.setmode(GPIO.BCM)             # choose BCM or BOARD
GPIO.setup(pin, GPIO.OUT)           # set GPIO23 as an output
counter = 0

###############################################################################

def on_connect(client, userdata, flags, rc):
    if rc == 0 and client.is_connected():
        print("Connected to MQTT Broker!")
        # Publish the Device config for auto discovery.
        msg = json.dumps(TOPIC_MAINCABIN_FAN_CONFIG_PAYLOAD)
        result = client.publish(TOPIC_MAINCABIN_FAN_CONFIG, msg)
        status = result[0]
        if status != 0:
            print(f'Failed to send SWITCH config to topic {TOPIC_MAINCABIN_FAN_CONFIG}')
        else:
            print(f'Successfully set SWITCH config to to topic {TOPIC_MAINCABIN_FAN_AVAILLABILTY}')
        # Publish the availlability - ONLINE
        result = client.publish(TOPIC_MAINCABIN_FAN_AVAILLABILTY, 'online')
        status = result[0]
        if status != 0:
            print(f'Failed to set avaiallability to {msg} for topic {TOPIC_MAINCABIN_FAN_AVAILLABILTY}')
        else:
            print(f'Successfully set avaiallability to {msg} for topic {TOPIC_MAINCABIN_FAN_AVAILLABILTY}')
        # TODO: Need to subscribe to the command channel.
        print(f'Subscribing tp topic {TOPIC_MAINCABIN_FAN_SET}')
        client.subscribe(TOPIC_MAINCABIN_FAN_SET)
    else:
        print(f'Failed to connect, return code {rc}')


def on_disconnect(client, userdata, rc):
    logging.info("Disconnected with result code: %s", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info("Reconnecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logging.info("Reconnected successfully!")
            # TODO: Need to publish availlability ONLINE
            msg = 'online'
            result = client.publish(TOPIC_MAINCABIN_FAN_AVAILLABILTY, 'online')
            status = result[0]
            if status != 0:
                print(f'Failed to set avaiallability to {msg} for topic {TOPIC_MAINCABIN_FAN_AVAILLABILTY} msg {msg}')
            else:
                print(f'Successfully set avaiallability to {msg} for topic {TOPIC_MAINCABIN_FAN_AVAILLABILTY} msg {msg}')
            # TODO: Maybe need to resubscribe?
            return
        except Exception as err:
            logging.error("%s. Reconnect failed. Retrying...", err)

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1
    logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)


def on_message(client, userdata, msg):
    # TODO: Need to filter the messages and set the pins.
    # TODO: Need to publish device state.
    print(f'Received `{msg.payload.decode()}` from `{msg.topic}` topic')
    match msg.payload.decode():
        case 'ON':
            # Set state to ON
            print(f'Recieved payload: {msg.payload.decode()}')
            set_state(client, 'ON')
            return
        case 'OFF':
            # Set state to off
            print(f'Recieved payload: {msg.payload.decode()}')
            set_state(client, 'OFF')
            return
        case _:
            print(f'Recieved UNKNOWN payload: {msg.payload.decode()}')
            return


def connect_mqtt():
    # TODO|: Need to update to a V2 interface.
    # But get it workking first lol
    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, CLIENT_ID)
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=120)
    client.on_disconnect = on_disconnect
    return client


def publish(client, topic, payload):
    msg = json.dumps(payload)
    if not client.is_connected():
        logging.error("publish: MQTT client is not connected!")
        time.sleep(1)
    result = client.publish(topic, msg)
    # result: [0, 1]
    status = result[0]
    if status == 0:
        print(f'Send `{msg}` to topic `{topic}`')
    else:
        print(f'Failed to send message to topic {topic}')
    time.sleep(1)


def set_state(client, state):
    # Get the state of the pin
    old_state = get_relay(pin)
    print(f'Initial state is {old_state}')
    if old_state:
        old_state = "ON"
    else:
        old_state =  "OFF"
    print(f'Initial state is {old_state} and the desired state is {state}')
    match state:
        case 'ON':
          print("Recivied ON Command.")
          if state != old_state:
              # set pin state
              set_relay(pin, GPIO.HIGH)
              # publish new state
              msg = json.dumps(state)
              result = client.publish(TOPIC_MAINCABIN_FAN_STATE, 'ON')
              print(f"Set pin {pin} to sate {state}")
          return
        case 'OFF':
          print("Recivied OFF command.")
          if state != old_state:
              # set pin state
              set_relay(pin, GPIO.LOW)
              # publish new state
              msg = json.dumps(state)
              result = client.publish(TOPIC_MAINCABIN_FAN_STATE, 'OFF')
              print(f"Set pin {pin} to sate {state}")
          return
        case _:
          print(f'set_state: Unknown state: {state}')
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
        print( "Keyboard interupt\n" ) # print value of counter

    except:
        # this catches ALL other exceptions including errors.
        # You won't get any error messages for debugging
        # so only use it once your code is working
        print( "Other error or exception occurred!" )

    finally:
        # this ensures a clean GPIO exit
        GPIO.cleanup()
        # TODO: Need to publish availlability OFFLINE
        if client.is_connected():
          # msg = json.dumps("offline")
          msg = 'offline'
          result = client.publish(TOPIC_MAINCABIN_FAN_AVAILLABILTY, 'offline')
          status = result[0]
          if status != 0:
              print(f'Failed to set avaiallability to OFFLINE for topic {TOPIC_MAINCABIN_FAN_AVAILLABILTY}')


if __name__ == '__main__':
    run()
