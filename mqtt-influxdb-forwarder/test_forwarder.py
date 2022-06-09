import unittest
import json
import datetime

# forwarder = __import__("forwarder.py")
import forwarder

class Test_ForwarderOnMessage(unittest.TestCase):
    ''' 
    test on_message callback function

    on_message strips out base topic from messages and filters messages on sub-topics and valid payload
    '''
    
    def setUp(self):
        '''
        '''
        import paho.mqtt.client as mqtt
        self.mqtt = mqtt
        # self.base_topic = forwarder.BASE_TOPIC
        topic = b""
        mid = 0
        self.message = mqtt.MQTTMessage(mid, topic)
        self.message.payload = b""

        forwarder.incoming_queue = []

        self.sensor_types = ['temperature', 'humidity', 'distance']

    def tearDown(self):
        '''
        '''
        pass

    def test_add_to_queue(self):
        '''
        check message added to queue
        iterates over list of topics
        '''
        # topics to check
        sub_topics_json = [
            'test/sensor-reading',
            'test/sensor-error',
        ]
        sub_topics = sub_topics_json[:]
        sensor_types = self.sensor_types
        for child_topic in ['sensor', 'sensors']:   # iterate over lists to generate repeating topics
            sub_topics.append(f'test/{child_topic}')
            for sensor_type in sensor_types:
                sub_topics.append(f'test/{child_topic}/{sensor_type}')

        for sub_topic in sub_topics:
            # reset queue to empty and check empty
            forwarder.incoming_queue = []
            self.assertEqual(len(forwarder.incoming_queue),0)

            # set message topic
            test_topic = forwarder.BASE_TOPIC + '/' + sub_topic
            expected_topic = '' + sub_topic
            self.message.topic = test_topic.encode()

            # set message payload
            if sub_topic in sub_topics_json:
                test_payload = {
                    'timestamp': 0,
                    'meta-date': {},
                    'measures': {}
                }
                self.message.payload = json.dumps(test_payload)
            else:
                test_payload = 5
                self.message.payload = test_payload #TODO: check how raw numbers are sent
            
            # expected response
            expected_payload = test_payload
            expected_response = [{
                'topic': expected_topic,
                'payload': expected_payload
            }]

            # test for queue length > 1
            for i in range(3):
                # call on_message() function
                forwarder.on_message(None, None, self.message)

                # test response
                with self.subTest(i):
                    self.assertEqual(len(forwarder.incoming_queue),i+1)
                    self.assertEqual(forwarder.incoming_queue[i]['topic'], expected_topic)
                    # self.assertDictEqual(forwarder.incoming_queue[i]['payload'], expected_payload)
                    self.assertDictEqual(forwarder.incoming_queue[i], expected_response[0])

    def test_not_added_to_queue(self):
        '''
        check message filtered out and not added to queue
        iterates over list of topics
        '''
        # topics to check
        sub_topics = ['messages', 'test/messages', 'test/messages/location']
        sub_topics.extend(self.sensor_types)

        for sub_topic in sub_topics:
            # reset queue to empty and check empty
            forwarder.incoming_queue = []
            self.assertEqual(len(forwarder.incoming_queue),0)

            # set message topic
            test_topic = forwarder.BASE_TOPIC + '/' + sub_topic
            # self.message.topic = test_topic.encode()

            # create message object
            message = self.mqtt.MQTTMessage(0, test_topic.encode())

            # add payload
            message.payload = json.dumps({})

            # call on_message() function
            forwarder.on_message(None, None, message)

            # test response
            with self.subTest(sub_topic):
                self.assertEqual(len(forwarder.incoming_queue),0)
    
    def test_empty_invalid_payload_json(self):
        '''
        check empty or invalid json payloads are caught and handled
        '''
        # topics to check
        sub_topics = ['test/sensor-reading', 'test/sensor-error', 'test/sensor', 'test/sensors']

        test_payloads = [
            {},
            [{}],
            # json.dumps({}),
            'string',
            '',
            bytes(4),
            # json.dumps('string'),
            7
        ]

        for sub_topic in sub_topics:
            for test_payload in test_payloads:
                # reset queue to empty and check empty
                forwarder.incoming_queue = []
                self.assertEqual(len(forwarder.incoming_queue),0)

                # set message topic
                test_topic = forwarder.BASE_TOPIC + '/' + sub_topic
                self.message.topic = test_topic.encode()

                # set message payload
                self.message.payload = test_payload

                # test response
                with self.subTest(sub_topic+':'+str(test_payloads.index(test_payload))):
                    # call on_message() function
                    forwarder.on_message(None, None, self.message)
                    # self.assertRaises((TypeError,ValueError), forwarder.on_message, None, None, self.message)
                    self.assertEqual(len(forwarder.incoming_queue),0)


class Test_ForwarderProcessQueue(unittest.TestCase):
    ''' test process_queue function
    '''

    def setUp(self):
        '''
        queue is a list of messages in the format
        queue = [{
            topic: value
            payload: value
        },...]
        '''
        self.now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f%Z")

        # define some reuseable payloads
        self.payload_timestamped = {
            'timestamp': self.now,
            'meta-data': {
                'device': 'unittest',
                'location': 'nowhere'
            },
            'measures': {
                'sensor1': 1.3,
                'sensor2': 2.4
            }
        }
        self.payload_oldtimestamp = {
            'timestamp': "2000-01-01T00:00:00Z",
            'meta-data': {
                'device': 'unittest',
                'location': 'nowhere'
            },
            'measures': {
                'sensor1': 1.3,
                'sensor2': 2.4
            }
        }
        self.payload_notimestamp = {
            'meta-data': {
                'device': 'unittest',
                'location': 'nowhere'
            },
            'measures': {
                'sensor1': 1.3,
                'sensor2': 2.4
            }
        }
        self.payload_missing_metadata = {
            'timestamp': self.now,
            'measures': {
                'sensor1': 1.3,
                'sensor2': 2.4
            }
        }
        self.payload_missing_measures = {
            'timestamp': self.now,
            'meta-data': {
                'device': 'unittest',
                'location': 'nowhere'
            },
        }
        self.payload_empty = {}
        self.payload_int = 5
        self.payload_string = 'string'

    def tearDown(self):
        '''
        '''
        pass

    def test_queue_reset(self):
        '''
        test that queue is emptied
        '''
        # reset to empty queue
        forwarder.incoming_queue = []
        
        # added some messages to queue
        for _ in range(2):
            message = {
                'topic': 'test/sensor-reading',
                'payload': self.payload_timestamped
            }
            forwarder.incoming_queue.append(message)
        
        # incoming_queue should be empty after process_queue
        forwarder.process_queue()
        self.assertFalse(forwarder.incoming_queue)

    def test_sensor_topics_map_to_measure(self):
        '''
        test that sensor-reading and sensor-error topics map to corresponding measures in db payload
        '''
        topics = ['sensor-reading', 'sensor-error']

        for topic in topics:
            # reset to empty queue
            forwarder.incoming_queue = []

            # add sensor-readings message
            message = {
                'topic': 'test/' + topic,
                'payload': self.payload_timestamped
            }
            forwarder.incoming_queue.append(message)

            # process queue
            response_payload = forwarder.process_queue()

            # test response
            response_measurement = response_payload[0]['measurement']
            expected_measurement = topic + 's'
            with self.subTest(topic):
                self.assertEqual(response_measurement, expected_measurement)
            # print(topic, 'maps')

    def test_not_sensor_topics_dont_map_to_any_measure(self):
        '''
        test that none sensor topics don't map to a measure in db payload
        '''
        topics = ['nonsense', 'test/nonsense', 'messages', 'test/messages/location']

        for topic in topics:
            # reset to empty queue
            forwarder.incoming_queue = []

            # add sensor-readings message
            message = {
                'topic': topic,
                'payload': self.payload_timestamped
            }
            forwarder.incoming_queue.append(message)

            # process queue
            response_payload = forwarder.process_queue()

            # test response payload is empty
            with self.subTest(topic):
                self.assertFalse(response_payload)

    def test_timestamp_maps(self):
        '''
        test that if timestamp exists and is current it is mapped to time
        '''
        # reset to empty queue
        forwarder.incoming_queue = []

        # add sensor-readings message
        message = {
            'topic': 'test/sensor-reading',
            'payload': self.payload_timestamped
        }
        forwarder.incoming_queue.append(message)

        # process queue
        response_payload = forwarder.process_queue()

        # print(response_payload)

        # test response
        response_time = response_payload[0]['time']
        expected_time = self.now
        self.assertEqual(response_time, expected_time)

    def test_notimestamp_maps(self):
        '''
        test that if no timestamp exists one is created and mapped to time
        '''
        # reset to empty queue
        forwarder.incoming_queue = []

        # add sensor-readings message
        message = {
            'topic': 'test/sensor-reading',
            'payload': self.payload_notimestamp
        }
        forwarder.incoming_queue.append(message)

        # process queue
        response_payload = forwarder.process_queue()

        print(response_payload)

        # test response
        # timestamp compare
        # response_time = datetime.datetime.timestamp(datetime.datetime.strptime(response_payload[0]['time'], "%Y-%m-%dT%H:%M:%S.%f"))
        # expected_time = datetime.datetime.timestamp(datetime.datetime.utcnow())
        # print(response_time)
        # print(expected_time)
        # self.assertAlmostEqual(response_time, expected_time, delta=2)

        # datetime compare
        response_time = datetime.datetime.strptime(response_payload[0]['time'], "%Y-%m-%dT%H:%M:%S.%f")
        expected_time = datetime.datetime.utcnow()
        # print(response_time)
        # print(expected_time)
        self.assertAlmostEqual(response_time, expected_time, delta=datetime.timedelta(seconds=15))

        # # string compare
        # response_time = response_payload[0]['time']
        # expected_time = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f%Z")
        # print(response_time)
        # print(expected_time)
        # self.assertEqual(response_time[:17], expected_time[:17])

    # test if old timestamp then generate current timestamp and map to time
    #TODO implement this in forwarder.process_queue

    def test_metadata_and_measures_map(self):
        '''
        test that meta-data maps to tags and measures map to fileds
        '''
        # reset to empty queue
        forwarder.incoming_queue = []

        # add sensor-readings message
        message = {
            'topic': 'test/sensor-reading',
            'payload': self.payload_timestamped
        }
        forwarder.incoming_queue.append(message)

        # process queue
        response_payload = forwarder.process_queue()

        response_tags = response_payload[0]['tags']
        expected_tags = self.payload_timestamped['meta-data']

        response_fields = response_payload[0]['fields']
        expected_fields = self.payload_timestamped['measures']

        # test response
        with self.subTest('tags'): 
            self.assertEqual(response_tags, expected_tags)
        with self.subTest('fields'):
            self.assertEqual(response_fields, expected_fields)

    def test_partial_payload_handled(self):
        '''
        test that missing parts of payload is handled
        '''
        with self.subTest('no meta-data'):
            # message should process, with no tags added to db_payload object
            # reset to empty queue
            forwarder.incoming_queue = []

            # add sensor-readings message
            message = {
                'topic': 'test/sensor-reading',
                'payload': self.payload_missing_metadata
            }
            forwarder.incoming_queue.append(message)

            # process queue
            response_payload = forwarder.process_queue()

            self.assertEqual(len(response_payload),1)
            self.assertFalse(response_payload[0]['tags'])   # tags should be empty

    def test_invalid_payload_handled(self):
        '''
        test that invalid payloads are handled
        
        messages should not be processed and added to db if their payloads are not valid for the db
           - payload with missing measures
           - empty dict payload
           - non dict payloads
        '''
        payloads = [self.payload_missing_measures, self.payload_empty, self.payload_int, self.payload_string]

        for payload in payloads:
            # reset to empty queue
            forwarder.incoming_queue = []

            # add sensor-readings message
            message = {
                'topic': 'test/sensor-reading',
                'payload': payload
            }
            forwarder.incoming_queue.append(message)

            # process queue
            response_payload = forwarder.process_queue()

            with self.subTest(payloads.index(payload)):
                self.assertEqual(len(response_payload),0)


if __name__ == '__main__':
    unittest.main()