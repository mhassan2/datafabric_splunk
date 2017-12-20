Changes - Apps:
./etc/apps/splunk_httpinput/local/inputs.conf
./etc/apps/Splunk_TA_kafka
./etc/apps/splunk_app_db_connect
./etc/apps/search

Changes - Indexers:
./var/lib/splunk/nifidata
./var/lib/splunk/splunkaccesscombine
./var/lib/splunk/kafkadata
./var/lib/splunk/mysqldata
./var/lib/splunk/summarydb

Steps:

1) rm -rf splunk
2) tar xvzf splunk-7.0.0-c8a78efdd40f-Linux-x86_64.tgz
3) tar xvzf indexes.tgz -C /opt/splunk
4) tar xvzf apps_configs.tgz -C /opt/splunk/etc/apps/
5) ** Do not run: /opt/splunk/bin/splunk start ** 
when users start the VM they will start splunk, which will create 60 days temp license
