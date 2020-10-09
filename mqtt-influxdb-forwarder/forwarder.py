#!/usr/bin/env python3
# script to forward MQTT data to and InfluxDB database

import paho.mqtt.client as mqtt
from influxdb import InfluxDBClient
import time, datetime
import json
import os

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

def on_connect(client, userdata, flags, rc):
    print("Connected flags: ", str(flags))
    print("Connected with result code: "+str(rc))
    msg = {
        'Connected Client ID': MQTT_CLIENT_ID,
        'Subscribed channel': subscribe_topic,
        'device': 'MQTT to InfluxDB forwarder',
        'message type': 'on-connect'
    }
    client.publish(BASE_TOPIC+'/messages', json.dumps(msg))
    client.subscribe(subscribe_topic)
    print("Subscribed to topic: " + subscribe_topic)

def on_message(client, userdata, msg):
    global incoming_queue
    print("Received a message on topic: " + msg.topic)

    # add topics to be processed to the list
    pass_topics = ['/sensor']

    # strip out base topic
    topic = msg.topic[len(BASE_TOPIC+'/'):]
    if any(pass_topic in topic for pass_topic in pass_topics) and topic != 'messages': # payload on device/sensor
        print(topic)
        message = {
            'topic': topic,
            'payload': json.loads(msg.payload)#.decode("utf-8")
        }
        print(message['payload'])
        incoming_queue.append(message)

def process_queue():
    global incoming_queue
    _queue = incoming_queue
    incoming_queue = []
    db_payload = []

    for message in _queue:
        db_point = {}

        print("Topic: {}".format(message['topic']))

        # process sensor readings
        if '/sensor' in message['topic']:
            last_child_topic = message['topic'].rsplit('/', 1)[1]
            print('last child topic: {}'.format(last_child_topic))

            if last_child_topic == "sensor-reading":
                db_point['measurement'] = 'sensor-readings'
            elif last_child_topic == "sensor-error":
                db_point['measurement'] = 'sensor-errors'
            else:
                break

            ## map timestamp
            # if timestamp exists
            if ('timestamp' in message['payload'].keys()):
                print('ts found')
                db_point['time'] = message['payload']['timestamp']
            else:
                db_point['time'] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f%Z")
                print('ts not found or too old')
            
            ## map tags
            db_point['tags'] = {}
            for k in message['payload']['meta-data'].keys():
                db_point['tags'][k] = message['payload']['meta-data'][k]

            ## map fields
            fields = {}
            for k in message['payload']['measures'].keys():
                fields[k] = message['payload']['measures'][k]
                print("key: {}".format(k))

            db_point['fields'] = fields

            db_payload.append(db_point)

    return db_payload


def main():
    # start
    print("Starting MQTT Forwarder...")
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
    print("InfluxDB version: ", db_client.ping())

    # check if database exists. if not, create it.
    if any(a['name'] == DB_NAME for a in db_client.get_list_database()):
        print('Database found: ', DB_NAME)
    else:
        print('Database not found. Creating...')
        db_client.create_database(DB_NAME)
        print('Database {} created'.format(DB_NAME))

    # Initialize the MQTT client that should connect to the Mosquitto broker
    mqtt_client = mqtt.Client(MQTT_CLIENT_ID)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    print('MQTT username: ', MQTT_USERNAME)
    print('MQTT password: ', MQTT_PASSWORD)
    mqtt_client.username_pw_set(username=MQTT_USERNAME, password=MQTT_PASSWORD)
    connOK=False
    while(connOK == False):
        try:
            mqtt_client.connect(MQTT_SERVER[0], MQTT_SERVER[1], 60)
            connOK = True
        except:
            connOK = False
        time.sleep(2)

    # Blocking loop to the Mosquitto broker
    # mqtt_client.loop_forever()
    mqtt_client.loop_start()

    while True:
        while len(incoming_queue) == 0:
            time.sleep(2)
        db_payload = process_queue()

        ## encode and send to database
        print(db_payload)
        try:
            db_client.write_points(db_payload)
            print("Finished writing to InfluxDB")
        except:
            print("** Error writing to InfluxDB **")

if __name__ == '__main__':
    main()