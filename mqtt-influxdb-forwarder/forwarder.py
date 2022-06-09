#!/usr/bin/env python3
# script to forward MQTT data to and InfluxDB database

import paho.mqtt.client as mqtt
from influxdb import InfluxDBClient
import time, datetime
import json
import os
import logging

# define constants
MQTT_SERVER = ('mqtt', 1883) # ip, port
MQTT_USERNAME = os.getenv('MQTT_USERNAME', 'mqtt')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', 'password')
BASE_TOPIC = os.getenv('BASE_TOPIC', 'mig-stack')
MQTT_CLIENT_ID = 'Forwarder'    # MQTT to InfluxDB forwarder
DB_SERVER = ('influxdb', 8086)   # ip, port
DB_USER = 'root'
DB_PASS = 'root'
DB_NAME = os.getenv('INFLUXDB_DATABASE', 'MIGStack')
# DB_TABLE = 'sensor-readings'

subscribe_topic = BASE_TOPIC+'/#'
incoming_queue = []

# config logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(funcName)s():%(lineno)s - %(message)s",
    handlers=[
        # logging.FileHandler("forwarder.log"),
        logging.StreamHandler()
    ]
)

# supported last child sensor topics
sensor_topics = ['temperature', 'humidity', 'distance']

def on_connect(client, userdata, flags, rc):
    logging.info(f"Connected flags: {str(flags)}")
    logging.info(f"Connected with result code: {str(rc)}")
    msg = {
        'Connected Client ID': MQTT_CLIENT_ID,
        'Subscribed channel': subscribe_topic,
        'device': 'MQTT to InfluxDB forwarder',
        'message type': 'on-connect'
    }
    client.publish(BASE_TOPIC+'/messages', json.dumps(msg))
    client.subscribe(subscribe_topic)
    logging.info(f"Subscribed to topic: {subscribe_topic}")

def on_message(client, userdata, msg):
    '''
    allow last child topics
        /sensor*
        /temperature
        /humidity
        /distance
    other topics or invalid payloads should be filtered out
    '''
    global incoming_queue
    logging.info(f"Received a message on topic: {msg.topic}")

    # # add topics to be processed to the list
    # pass_topics = ['/sensor']

    # strip out base topic
    topic = msg.topic[len(BASE_TOPIC+'/'):]
    topic_parts = topic.split('/')

    # if last child topic is sensor type, payload should be numeric # else if last child topic is 'sensor', payload should be json
    if (topic_parts[-1] in sensor_topics and len(topic_parts) >= 2) or topic_parts[-1].startswith('sensor'):
        logging.info(f'Processing topic: {topic}')

        try:
            payload = float(msg.payload) if topic_parts[-1] in sensor_topics else json.loads(msg.payload)#.decode("utf-8")
            logging.info(f'  With payload: {payload}')
            message = {
                'topic': topic,
                'payload': payload
            }
        except TypeError:   # catch invalid json deserialise
            logging.warning(f"Invalid payload Type: {msg}")
            # raise
        except ValueError:
            logging.warning(f"Invalid payload Value: {msg}")
            # raise
        else:
            incoming_queue.append(message)

def process_queue():
    global incoming_queue
    _queue = incoming_queue
    incoming_queue = []
    db_payload = []

    for message in _queue:
        db_point = {}

        logging.info(f"Topic: {message['topic']}")

        topic_parts = message['topic'].split('/')
        logging.info(f'last child topic: {topic_parts[-1]}')

        # if topic numeric
        if topic_parts[-1] in sensor_topics and len(topic_parts) >= 2 and isinstance(message['payload'], (int,float)):
            logging.info('processing payload as numeric')
            db_point['measurement'] = 'sensor-readings'
            db_point['time'] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f%Z")
            db_point['tags'] = {'id': topic_parts[0]}
            db_point['fields'] = {
                f'{topic_parts[-1]}': message['payload']    #TODO consider wrapping payload in float()
            }
            db_payload.append(db_point)

        # elif topic json
        elif topic_parts[-1].startswith('sensor') and isinstance(message['payload'], dict) and any(k in message['payload'].keys() for k in ['measures','fields']):
            logging.info('processing payload as json')

            ## set measure
            if topic_parts[-1] == "sensor-error":
                db_point['measurement'] = 'sensor-errors'
            else:
                db_point['measurement'] = 'sensor-readings'

            ## map timestamp
            # if timestamp exists
            t_keys = [k for k in ['timestamp','time'] if k in message['payload'].keys()]
            if t_keys:
                logging.info(f'ts found: {t_keys}')
                db_point['time'] = message['payload'][t_keys[0]]
            else:
                logging.info('ts not found')
                db_point['time'] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f%Z")
            #TODO check if ts too old; i.e. epoch 0

            ## map tags
            db_point['tags'] = {}
            tag_keys = [k for k in ['meta-data','tags'] if k in message['payload'].keys()]
            if tag_keys:
                logging.info(f'tags found: {tag_keys}')
                for k in message['payload'][tag_keys[0]].keys():
                    db_point['tags'][k] = message['payload'][tag_keys[0]][k]

            ## map fields
            db_point['fields'] = {}
            f_keys = [k for k in ['measures','fields'] if k in message['payload'].keys()]
            if f_keys:
                logging.info(f'fields found: {f_keys}')
                for k in message['payload'][f_keys[0]].keys():
                    logging.info(f'key: {k}')
                    db_point['fields'][k] = message['payload'][f_keys[0]][k]

            db_payload.append(db_point)

        else:
            logging.info('not processing')

    return db_payload


def main():
    # start
    logging.info("Starting MQTT Forwarder...")
    # pause awhile while other containers startup
    time.sleep(50)

    # Set up a client for InfluxDB
    connOK=False
    while(connOK == False):
        try:
            db_client = InfluxDBClient(DB_SERVER[0], DB_SERVER[1], DB_USER, DB_PASS, DB_NAME)
            connOK = True
        except:
            connOK = False
        time.sleep(2)
    logging.info(f"InfluxDB version: {db_client.ping()}")

    # check if database exists. if not, create it.
    if any(a['name'] == DB_NAME for a in db_client.get_list_database()):
        logging.info(f'Database found: {DB_NAME}')
    else:
        logging.info('Database not found. Creating...')
        db_client.create_database(DB_NAME)
        logging.info('Database {} created'.format(DB_NAME))

    # Initialize the MQTT client that should connect to the Mosquitto broker
    mqtt_client = mqtt.Client(MQTT_CLIENT_ID)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.username_pw_set(username=MQTT_USERNAME, password=MQTT_PASSWORD)
    connOK=False
    while(connOK == False):
        try:
            mqtt_client.connect(MQTT_SERVER[0], MQTT_SERVER[1], 60)
            connOK = True
        except:
            connOK = False
        time.sleep(2)
    logging.info('Connected to MQTT server')

    # Blocking loop to the Mosquitto broker
    # mqtt_client.loop_forever()
    mqtt_client.loop_start()

    while True:
        while len(incoming_queue) == 0:
            time.sleep(2)
        db_payload = process_queue()

        ## encode and send to database
        logging.info(db_payload)
        try:
            db_client.write_points(db_payload)
            logging.info("Finished writing to InfluxDB")
        except:
            logging.warning(f"** Error writing to InfluxDB ** :{db_payload}")

if __name__ == '__main__':
    main()