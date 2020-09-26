# Docker MQTT-InfluxDB Forwarder

Docker container with python script that forwards MQTT messages into an InfluxDB database.

The forwarder script subsribes to all messages on a given base topic. The forwarder then filters and processes received messages, before writing data points to an InfluxDB database.

<br />

## MQTT Message Structure

Received MQTT messages are expected to be structured as follows. The forwarder script will need to be modified if different structured messages are needed.

### MQTT Topics

All messages on the base topic are subscribed to: i.e. `BASE_TOPIC+'/#'`. The following sub-topics are processed. All other sub-topics are ignored.

| Topic | Description |
| --- | --- |
| last child topic: `/sensor-reading` | Any message with the last child topic of `sensor-reading`. |
| last child topic: `/sensor-errors` | Any message with the last child topic of `sensor-errors`. |

<br />

### MQTT Payload

The MQTT payload is expected to be in the format:

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
