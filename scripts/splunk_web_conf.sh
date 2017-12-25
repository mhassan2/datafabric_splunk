#!/bin/bash

#set home screen banner in web.conf
fullhostname=`echo $HOSTNAME`
ip="127.0.0.1"
container_ip=`hostname --ip-address`
platforms_label="MySQL Hadoop Kafka Apache NIFI"
USERADMIN="admin"
USERPASS="splunk123"
SHOW_PASS="splunk123"

SPLUNK_VER=`cat /opt/splunk/etc/splunk.version | grep VERSION|cut -d "=" -f2`
#MYSQL_VER=`mysql -h localhost -V|awk '{print $5}'|sed 's/,//'`
#HADOOP_VER=`ls -l /opt/|grep hadoop|awk '{print $9}'| sed 's/hadoop-//'`

HADOOP_VER=`ls -l /opt/|grep hadoop|awk '{print $9}'| sed 's/hadoop-//'`
YARN_VER="n/a"
ZOOKEEPER_VER="n/a"
#ZOOKEEPER_VER=`ls -l /opt/|grep zookeeper|awk '{print $9}'| sed 's/zookeeper-//'`
MYSQL_VER=`mysql -h localhost -V|awk '{print $5}'|sed 's/,//'`
KAFKA_VER=`ls -l /opt/|grep kafka|awk '{print $9}'| sed 's/kafka_//'`
NIFI_VER=`ls -l /opt/|grep nifi|awk '{print $9}'| sed 's/nifi-//'`
JAVA_VER=`java -version`
SUPERVISOR_VER=3.0


supervisor_url="<a href=\"http://localhost:9001\" >http://localhost:9001</a>"
hadoop_url="<a href=\"http://localhost:50070\" >http://localhost:50070</a>"
nifi_url="<a href=\"http://localhost:9090/nifi\" >http://localhost:9090/nifi</a>"
yarn_url="<a href=\"http://localhost:8088\" >http://localhost:8088</a>"
mysql_url="n/a"
kafka_url="n/a"
zookeeper_url="n/a"
#tutorial_url="<font color=\"lime\" <a href=\"https://github.com/mhassan2/datafabric_splunk/wiki\" >[Click Here For Step By Step Exercises] </a></font>"
tutorial_url="<a href=\"https://github.com/mhassan2/datafabric_splunk/wiki\" >https://github.com/mhassan2/datafabric_splunk/wiki </a>"

touch /opt/splunk/etc/.ui_login	#prevent first time changeme password screen`
/opt/splunk/bin/splunk edit user $USERADMIN -password $USERPASS -roles admin -auth admin:changeme

#-------web.conf stuff-------
LINE1="<CENTER><H2><font color=\"blue\"> &nbsp; Data Fabric Integration Sandbox &nbsp; </font></H2><br/></CENTER>"

#tutorial
#LINE2=" <H3 style=\"text-align: left;\"><font color=\"white\"> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Tutorial: </font> &nbsp;&nbsp;$tutorial_url </H3>"
LINE2=" <H3 style=\"text-align: left;\"><font color=\"white\"> &nbsp;&nbsp;&nbsp;&nbsp; Tutorial: </font> &nbsp;$tutorial_url </H3>"

#hostname
#LINE3=" <H3 style=\"text-align: left;\"><font color=\"#867979\"> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; Hostname: </font><font color=\"#FF9033\"> $fullhostname &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; <font color=\"#867979\">  Host IP: </font><font color=\"#FF9033\"> $ip</font></H3>"

#useradmin
LINE3="<CENTER><H3 style=\"text-align: left;\" <font color=\"white\">&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; User: </font> <font color=\"red\">$USERADMIN</font> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; <font>Password:</font> <font color=\"red\"> $USERPASS</font></H3></font></CENTER>"

#supervisor
LINE4=" <H3 style=\"text-align: left;\"><font color=\"#867979\"> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; SUPERVISOR:</font><font color=\"#FF9033\"> $SUPERVISOR_VER   &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; <font color=\"#867979\">  URL: </font><font color=\"#FF9033\"> $supervisor_url</font></H3>"

#nifi
LINE5=" <H3 style=\"text-align: left;\"><font color=\"#867979\"> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; NIFI:</font><font color=\"#FF9033\"> $NIFI_VER &nbsp;&nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; <font color=\"#867979\">  URL: </font><font color=\"#FF9033\"> $nifi_url</font></H3>"

#hadoop
LINE6=" <H3 style=\"text-align: left;\"><font color=\"#867979\"> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; HADOOP:</font><font color=\"#FF9033\"> $HADOOP_VER  &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; <font color=\"#867979\">  URL: </font><font color=\"#FF9033\"> $hadoop_url</font></H3>"

#yarn
LINE7=" <H3 style=\"text-align: left;\"><font color=\"#867979\"> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; YARN:</font><font color=\"#FF9033\"> $YARN_VER &nbsp; &nbsp;&nbsp; &nbsp; &nbsp;&nbsp;&nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; <font color=\"#867979\">  URL: </font><font color=\"#FF9033\"> $yarn_url</font></H3>"

#kafka
LINE8=" <H3 style=\"text-align: left;\"><font color=\"#867979\"> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; KAFAK:</font><font color=\"#FF9033\"> $KAFKA_VER  &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; <font color=\"#867979\">  URL: </font><font color=\"#FF9033\"> $kafka_url</font></H3>"

#zk
LINE9=" <H3 style=\"text-align: left;\"><font color=\"#867979\"> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ZOOKEEPER:</font><font color=\"#FF9033\"> $ZOOKEEPER_VER   &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; <font color=\"#867979\">  URL: </font><font color=\"#FF9033\"> $zookeeper_url</font></H3>"

#mysql
LINE10=" <H3 style=\"text-align: left;\"><font color=\"#867979\"> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; MySQL:</font><font color=\"#FF9033\"> $MYSQL_VER  &nbsp;&nbsp;&nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; <font color=\"#867979\">  URL: </font><font color=\"#FF9033\"> $mysql_url</font></H3>"


#configure the custom login screen and http access for ALL (no exception)
custom_web_conf="[settings]\nlogin_content=<div align=\"right\" style=\"border:2px solid green;\"> $LINE1 $LINE2 $LINE3 $LINE4 $LINE5 $LINE6 $LINE7 $LINE8 $LINE9 $LINE10 $LINE11 </div> <p><font color="\#867979\#"  <a href=\"https://github.com/mhassan2/datafabric_splunk\"  >https://github.com/mhassan2/datafabric_splunk </a>  &nbsp;&nbsp;&nbsp; (container internal IP=$container_ip) </font></p> \n\nenableSplunkWebSSL=0\n"

printf "$custom_web_conf" > /tmp/web.conf
cp /tmp/web.conf /opt/splunk/etc/system/local/web.conf
#-------web.conf stuff-------

#restarting splunkweb may not work with 6.5+
/opt/splunk/bin/splunk restart splunkweb -auth $USERADMIN:$USERPASS
#/opt/splunk/bin/splunk restart
echo $MAINTAINER

