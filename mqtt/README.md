# Docker Mosquitto

Docker container for running Mosquitto MQTT broker.

```bash
docker build -t mqtt .
docker create --name mqtt mqtt
```

```bash
docker run -it -p 1883:1883 -p 9001:9001 -v mosquitto.conf:/mosquitto/config/mosquitto.conf mqtt
```

Configuration is copied into the build. Alternatively, it could be mounted when the container is run.

```bash
-v mosquitto.conf:/mosquitto/config/mosquitto.conf
```


## References

* https://philhawthorne.com/setting-up-a-local-mosquitto-server-using-docker-for-mqtt-communication/
* https://hub.docker.com/_/eclipse-mosquitto
* https://docs.docker.com/samples/library/eclipse-mosquitto/
