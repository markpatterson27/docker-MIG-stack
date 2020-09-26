# Docker Influxdb

Docker container for running Influxdb.

A default database, retention policies and continuous queries are automatically created.

Retention policies created:
- default policy keeps data for 2 weeks
- second policy keeps data for 4 years

Continuous queries created:
- first cq averages data over 60 minute period before copying to 4 years
- second policy just copies data across


## References

* https://hub.docker.com/_/influxdb
