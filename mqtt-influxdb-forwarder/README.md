# Docker MQTT-InfluxDB Forwarder

Docker container with python script that forwards MQTT messages into an InfluxDB database.

The forwarder script subscribes to all messages on a given base topic. The forwarder then filters and processes received messages, before writing data points to an InfluxDB database.

<br />

## MQTT Message Structure

Received MQTT messages are expected to be structured as follows. The forwarder script will need to be modified if different structured messages are needed.

### MQTT Topics

All messages on the base topic are subscribed to: i.e. `BASE_TOPIC+'/#'`. The following sub-topics are processed. All other sub-topics are ignored.

| Topic | Description |
| --- | --- |
| last child topic: [`/sensor-reading`, `/sensor`] | Any message with the last child topic of `sensor-reading`, `sensor` or `sensors`. |
| last child topic: `/sensor-errors` | Any message with the last child topic of `sensor-errors`. |
| last child topic: [`/temperature`, `/humidity`, `/distance`] | Message with the last child topic one of [`/temperature`, `/humidity`, `/distance`] and with a middle child topic. Middle child topic will be used as a tag. |

<br />

### MQTT Payloads

The MQTT payload is expected to be in one of the following formats:

| Topic | Payload |
| --- | --- |
| base-topic/+/sensor<br>base-topic/+/sensor-reading<br>ase-topic/+/sensor-error | JSON |
| base-topic/+/temperature<br>base-topic/+/sensor/temperature | Single number<br>+ middle topic parsed as ID tag |



#### JSON

If the last child topic contains `sensor` the payload is expect to be in JSON with the following keys.

```js
payload {
    "timestamp": "<timestamp of reading>",
    "meta-data": {
        // this is data that doesn't need to be graphed or processed,
        // but could be used for filtering
        // this data is likely to be strings and unlikely to be numerical
        "<dictionary of meta-data associated with sensor reading>"
    },
    "measures": {
        // this is data that will be processed and/or graphed
        // this data will be numerical
        "<dictionary of sensor readings>"
    }
}
```

Alternative keys

```js
payload {
    "time": "<timestamp of reading>",
    "tags": {
        "<dictionary of meta-data associated with sensor reading>"
    },
    "fields": {
        "<dictionary of sensor readings>"
    }
}
```

#### Single Numeric Value

Messages with a last child topic that is a sensor type will have a payload with a single numeric value. Middle child topic will be used as a ID tag.

```
Topic: /_sensor-type_
Payload: single numeric value
```

## InfluxDB Data Points

InfluxDB data points contain a `time` timestamp, at least one `fields`, and optionally `tags`. MQTT message payloads are mapped to InfluxDB data points as such:

| MQTT Payload | InfluxDB Data Point | Description |
| --- | --- | --- |
| last child topic | "measurement" | table in database that datapoint written to. |
| "timestamp" | "time"| `timestamp` is mapped directly to `time`. If a timestamp is not in the MQTT payload, a timestamp is generated. |
| "meta-data" | "tags" | Any `meta-data` key:value pairs are mapped to influxdb `tags`. |
| "measures" | "fields" | Any `measures` key:value pairs are mapped to influxdb `fields`. |


## References

- https://pypi.org/project/paho-mqtt/
- https://pypi.org/project/influxdb/
