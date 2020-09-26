# FROM toke/mosquitto
FROM eclipse-mosquitto

ARG MQTT_USERNAME
ARG MQTT_PASSWORD

ENV USERNAME "${MQTT_USERNAME}"
ENV PASSWORD "${MQTT_PASSWORD}"

RUN echo "${USERNAME}:${PASSWORD}" >> /mosquitto/config/pwfile
RUN mosquitto_passwd -U /mosquitto/config/pwfile

COPY ./mosquitto.conf /mosquitto/config/mosquitto.conf
