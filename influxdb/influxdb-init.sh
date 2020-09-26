#!/bin/bash
# create database, retention policies and continuous queries 

influx -execute "CREATE DATABASE $DEFAULT_DATABASE"

##
# below queries create two retention policies
#   - default policy keeps data for 2 weeks
#   - second policy keeps data for 4 years
#
# continuous queries copy data from 2 weeks policy to the 4 years policy
#   - first cq averages data over 60 minute period before copying to 4 years
#   - second policy just copies data across
##

# retention policies
influx -execute "CREATE RETENTION POLICY \"2_weeks\" ON \"$DEFAULT_DATABASE\" DURATION 2w REPLICATION 1 DEFAULT"
influx -execute "CREATE RETENTION POLICY \"4_years\" ON \"$DEFAULT_DATABASE\" DURATION 208w REPLICATION 1"

# continuous queries
influx -execute "CREATE CONTINUOUS QUERY \"cq_1h\" ON $DEFAULT_DATABASE BEGIN \
 SELECT mean(*) INTO \"4_years\".\"sensor-readings\" FROM \"2_weeks\".\"sensor-readings\" \
 GROUP BY time(60m), * \
END"
influx -execute "CREATE CONTINUOUS QUERY \"cq_copy_across\" ON $DEFAULT_DATABASE BEGIN \
 SELECT * INTO \"4_years\".\"sensor-errors\" FROM \"2_weeks\".\"sensor-errors\" \
END"
