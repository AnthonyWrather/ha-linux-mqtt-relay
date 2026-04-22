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
import datetime as dt

from paho.mqtt import client as mqtt_client
from configparser import ConfigParser

###############################################################################
# Set up the config options.
config = ConfigParser(delimiters=('=', ))
config.read('config.ini')

sensor_type = config['sensor'].get('type', 'dht22').lower()

###############################################################################

BROKER = config['mqtt'].get('broker', 'homeassistant.local').lower()
PORT = int(config['mqtt'].get('port', '1883'))
# generate client ID with pub prefix randomly
CLIENT_ID = f'python-mqtt-tcp-pub-sub-{random.randint(0, 1000)}'
USERNAME = config['mqtt'].get('username', 'CONFIG_ME')
PASSWORD = config['mqtt'].get('password', 'CONFIG_ME')

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = config['mqtt'].get('timeout', '60').lower()

# Define the main device and a single sensor.
# Publish here to create or update the device.
TOPIC_BASE = config['homeassistant'].get('topic_base', 'default/homeassistant/switch').lower() \
    + '/relay' + config['homeassistant'].get('device_name', '/device').lower()
TOPIC_MAINCABIN_RELAY_CONFIG = TOPIC_BASE + config['mqtt'].get('topic_config', '/config').lower()

# Update Payload to ON/OFF
# Set to the current state of the relay ON/OFF.
# Publish here to broadcast the current state of the device.
TOPIC_MAINCABIN_RELAY_STATE = TOPIC_BASE + config['mqtt'].get('topic_state', '/state').lower()
TOPIC_MAINCABIN_RELAY_STATE_EXAMPLE = {
  'on'
}

# Command Payload  ON/OFF
# Receive a command to set the relay ON/OFF.
# Subscribe here to get commands.
TOPIC_MAINCABIN_RELAY_SET = TOPIC_BASE + config['mqtt'].get('topic_set', '/set').lower()
TOPIC_MAINCABIN_RELAY_SET_EXAMPLE = {
  'on'
}


# availability Payload  ONLINE/OFFLINE
# Set to ONLINE on start and OFFLINE on exit.
# Publish here to say this device is available.
TOPIC_MAINCABIN_RELAY_AVAILABILITY = TOPIC_BASE + config['mqtt'].get('topic_availability', '/availability').lower()
TOPIC_MAINCABIN_RELAY_AVAILABILITY_EXAMPLE = {
  'online'
}

TOPIC_MAINCABIN_RELAY_CONFIG_PAYLOAD = {
  "device_class":"switch",
  "name": "Switch-01",
  "state_topic": TOPIC_MAINCABIN_RELAY_STATE,
  "command_topic": TOPIC_MAINCABIN_RELAY_SET,
  "availability_topic": TOPIC_MAINCABIN_RELAY_AVAILABILITY,
  "value_template":"{{value_json.switch}}",
  "optimistic": "false",
  "qos": "0",
  "retain": "true",
  "unique_id": "switch_01",
  "device": {
    "identifiers": ["relay_01"],
    "name": "Relay-01",
    "manufacturer": "Example Sensors Ltd.",
    "model": "Example Relay",
    "model_id": "On-Off-Switch",
    "hw_version": "Linux-0.01a",
    "sw_version": "2026.4.0",
    "configuration_url": "https://github.com/AnthonyWrather/ha-linux-mqtt-relay"
  }
}


# These will move to a config file.
pin = int(config['sensor'].get('pin', '23').lower())
GPIO.setmode(GPIO.BCM)             # choose BCM or BOARD
GPIO.setup(pin, GPIO.OUT)           # set GPIO23 as an output

###############################################################################

def on_connect(client, userdata, flags, rc):
    if rc == 0 and client.is_connected():
        logging.info("Connected to MQTT Broker!")
        # Publish the Device config for auto discovery.
        msg = json.dumps(TOPIC_MAINCABIN_RELAY_CONFIG_PAYLOAD)
        result = client.publish(TOPIC_MAINCABIN_RELAY_CONFIG, msg)
        status = result[0]
        if status != 0:
            logging.info(f'Failed to send SWITCH config to topic {TOPIC_MAINCABIN_RELAY_CONFIG}')
        else:
            logging.info(f'Successfully sent SWITCH config to to topic {TOPIC_MAINCABIN_RELAY_CONFIG}')
        # Publish the availability - ONLINE
        result = client.publish(TOPIC_MAINCABIN_RELAY_AVAILABILITY, 'online')
        status = result[0]
        if status != 0:
            logging.info(f'Failed to set availability to online for topic {TOPIC_MAINCABIN_RELAY_AVAILABILITY}')
        else:
            logging.info(f'Successfully set availability to online for topic {TOPIC_MAINCABIN_RELAY_AVAILABILITY}')
        logging.info(f'Subscribing to topic {TOPIC_MAINCABIN_RELAY_SET}')
        client.subscribe(TOPIC_MAINCABIN_RELAY_SET)
    else:
        logging.info(f'Failed to connect, return code {rc}')


def on_disconnect(client, userdata, rc):
    logging.info("Disconnected with result code: %s", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info("Reconnecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logging.info("Reconnected successfully!")
            result = client.publish(TOPIC_MAINCABIN_RELAY_AVAILABILITY, 'online')
            status = result[0]
            if status != 0:
                logging.info(f'Failed to set availability to online for topic {TOPIC_MAINCABIN_RELAY_AVAILABILITY}')
            else:
                logging.info(f'Successfully set availability to online for topic {TOPIC_MAINCABIN_RELAY_AVAILABILITY}')
            # TODO: Discover if there is any scenario where I need to resubscribe?
            return
        except Exception as err:
            logging.error("%s. Reconnect failed. Retrying...", err)

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1

    logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)


def on_message(client, userdata, msg):
    # TODO: Need to rewite this to use the native 1 and 0 which avoids the conversion.
    logging.info('==================================================================')
    logging.info(f'Message `{msg.payload.decode()}` from `{msg.topic}` topic')
    match msg.payload.decode():
        case 'ON':
            # Set state to ON
            logging.info(f'Received payload: {msg.payload.decode()}')
            set_state(client, 'ON')
            return
        case 'OFF':
            # Set state to off
            logging.info(f'Received payload: {msg.payload.decode()}')
            set_state(client, 'OFF')
            return
        case _:
            logging.info(f'Received UNKNOWN payload: {msg.payload.decode()}')
            return


def connect_mqtt():
    # TODO: Need to update this to a V2 interface.
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info("Connecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)
        try:
            client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, CLIENT_ID)
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
    logging.info(f'Sending Message `{msg}` to `{topic}` topic')
    if not client.is_connected():
        logging.error("publish: MQTT client is not connected!")
        time.sleep(1)
    result = client.publish(topic, msg)
    # result: [0, 1]
    status = result[0]
    if status == 0:
        logging.info(f'Send `{msg}` to topic `{topic}`')
    else:
        logging.info(f'Failed to send message to topic {topic}')
    time.sleep(1)


def set_state(client, state):
    # Get the state of the pin
    old_state = get_relay(pin)
    if old_state:
        old_state = "ON"
    else:
        old_state =  "OFF"
    logging.info(f'Initial pin state is {old_state} and the desired state is {state}')
    match state:
        case 'ON':
          logging.info("Received ON Command.")
          if state != old_state:
              # set pin state
              logging.info(f"Set pin {pin} to sate {state}")
              set_relay(pin, GPIO.HIGH)
          # publish new state
          logging.info(f"Set state {TOPIC_MAINCABIN_RELAY_STATE} to sate ON")
          result = client.publish(TOPIC_MAINCABIN_RELAY_STATE, 'ON')
          return
        case 'OFF':
          logging.info("Received OFF command.")
          if state != old_state:
              # set pin state
              logging.info(f"Set pin {pin} to sate {state}")
              set_relay(pin, GPIO.LOW)
          # publish new state
          logging.info(f"Set state {TOPIC_MAINCABIN_RELAY_STATE} to sate OFF")
          result = client.publish(TOPIC_MAINCABIN_RELAY_STATE, 'OFF')
          return
        case _:
          logging.info(f'set_state: Received unknown state: {state}')
          return


def set_relay( pin, state ):
    GPIO.output(pin, state)


def get_relay(pin):
    return GPIO.input(pin)


def dump_config_ini():
    print("\n===================================================================")
    print("config.ini")
    print("[mqtt]")
    print(f"broker = {config['mqtt'].get('broker').lower()}")
    print(f"username = {config['mqtt'].get('username')}")
    # print(f"password = {config['mqtt'].get('password')}")
    print("password = ***REDACTED***")
    print(f"port = {config['mqtt'].get('port').lower()}")
    print(f"timeout = {config['mqtt'].get('timeout').lower()}")
    print("[sensor]")
    print(f"pin = {config['sensor'].get('pin').lower()}")
    print(f"type = {config['sensor'].get('type').lower()}")
    print(f"interval = {config['sensor'].get('interval').lower()}")
    print(f"decimal_digits = {config['sensor'].get('decimal_digits').lower()}")
    print("[homeassistant]")
    print(f"device_name = {config['homeassistant'].get('device_name').lower()}")
    print(f"topic_base = {config['homeassistant'].get('topic_base').lower()}")
    print(f"topic_config = {config['homeassistant'].get('topic_config').lower()}")
    print(f"topic_state = {config['homeassistant'].get('topic_state').lower()}")
    print(f"topic_set = {config['homeassistant'].get('topic_set').lower()}")
    print(f"topic_availability = {config['homeassistant'].get('topic_availability').lower()}")
    print("===================================================================\n")


def dump_topic_config():
    print("\n===================================================================")
    print("Topic Configuration")
    print(f"BROKER: {BROKER}")
    print(f"TOPIC: {TOPIC_MAINCABIN_RELAY_CONFIG}")
    print(f"PAYLOAD: \n{json.dumps(TOPIC_MAINCABIN_RELAY_CONFIG_PAYLOAD, indent=2)})")
    print("===================================================================\n")


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

    except:
        # this catches ALL other exceptions including errors.
        # You won't get any error messages for debugging
        # so only use it once your code is working
        logging.info( "A general exception occurred!" )

    finally:
        # this ensures a clean GPIO exit
        GPIO.cleanup()
        # TODO: Need to publish availability OFFLINE
        if client is not None and client.is_connected():
          result = client.publish(TOPIC_MAINCABIN_RELAY_AVAILABILITY, 'offline')
          status = result[0]
          if status != 0:
              logging.info(f'Failed to set availability to OFFLINE for topic {TOPIC_MAINCABIN_RELAY_AVAILABILITY}')


if __name__ == '__main__':
    # Need to dump the config.
    # dump_config_ini()
    dump_topic_config()
    run()
