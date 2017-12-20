## Introduction:
The purpose of this docker container  is to correlate the components that make up the Splunk data fabric embrace initiative process. The practitioners can now immediately try and experience the power of a Splunk integration with different external software components like Hadoop, RDBMS, Kafka and Nifi, with the ability to search, visualize and analyze the pre-populated data. There is no hassle of setting them up separately!

# Pull in local copy of this repository (optional):
``
https://github.com/mhassan2/datafabric_splunk
```

## Prerequisites (Mac OSX):
1. Install docker and allocate all available memory and CPU to docker daemon:
   \> preference \-> advance \-> slide CPU and Memory line all the way to the right \-> apply & restart

2. Increase your docker storage pool from 10G to 20G (this is distrucive and will delete all volumes, containers and images)

```
cd ~/Library/Containers/com.docker.docker/Data/database/
git reset --hard

cat com.docker.driver.amd64-linux/disk/size
```
Number is in MB, so 20G should be 20971520:
```
echo 20971520 > com.docker.driver.amd64-linux/disk/size
git add com.docker.driver.amd64-linux/disk/size
git commit -s -m 'New target disk size'
```
then
```
rm ~/Library/Containers/com.docker.docker/Data/com.docker.driver.amd64-linux/Docker.qcow2
Make sure to restart docker.
```
There's no OSX UI support for this change at this point. For Linux change follow instructions here: https://bobcares.com/blog/docker-container-size/



## Note:

 - All passwords in this tutorial are preset to “splunk123” (applies to everything).
 - Please to not disable sshd, hadoop uses rsync to communicate with the nodes.

## Pre-installed and pre-configured packages:
- hadoop-2.9.0 (yarn)	http://apache.claz.org/hadoop/common/hadoop-2.9.0/hadoop-2.9.0.tar.gz
- kafka_2.11-1.0.0		http://apache.claz.org/kafka/1.0.0/kafka_2.11-1.0.0.tgz
- Apache nifi-1.4.0			http://apache.claz.org/nifi/1.4.0/nifi-1.4.0-bin.tar.gz
- MySQL 5.5.58-0+deb8u1		(using apt-get. See Dockerfile)
- java version  1.8.0_151	(using apt-get. see Dockerfile)
- splunk v7.0.1				https://www.splunk.com/en_us/download/splunk-enterprise.html
- Splunk mysql-connector-java-5.1.44 https://dev.mysql.com/get/Downloads/Connector-J/mysql-connector-java-5.1.44.tar.gz
- Splunk dbconnect v3.11	https://splunkbase.splunk.com/app/2686/

- Splunk Kafka addon (disabled)	https://splunkbase.splunk.com/app/2935/
- Splunk Kafka connector (beta/disabled)
- Virtual indexers and sample dashboards


## Pre-loaded datasets:
- world.sql.gz	 http://downloads.mysql.com/docs/world.sql.gz
- Hunkdata.json.gz http://www.splunk.com/web_assets/hunk/Hunkdata.json.gz
- Sample Avro dataset  (copy avialable in data directory)
- Sample kafka dataset (copy avialalbe in data directory)


## Docker commands:

Login:
```
-The standard practice is:      docker exec DF01 /bin/bash
-Also using ssh on port 2122:   ssh -p 2122 root@localhost
```


To copy files to container:   ```docker cp localfilename  DF01:/tmp```

To start a container:	```docker start DF01```

To create a container (first time will take ~5 mins while pulling image. ignore + sign ):

```diff
+ docker run -d --name=DF01 --hostname=DF01 -p 2122:22 -p 8000:8000 -p 8088:8088 -p 8188:8188 -p 10020:10020 -p 9090:9090 -p 50070:50070  splunknbox/splunk_datafabric
```

If you dont provide the environmental vars with the run command it will assume it is set to "YES".

To prevent a service from staring set the var to "NO". Example, run all services except MySQL:
```
time docker run -d --name=DF01 --hostname=DF01 -p 2122:22 -p 8000:8000 -p 8088:8088 -p 8188:8188 -p 10020:10020 -p 9090:9090 -p 50070:50070 -e MYSQL="NO"  splunknbox/splunk_datafabric

Available vars you can use with docker run command:
MYSQL
KAKFA
NIFI
HDFS
```

Docker run command shows all ports for external services. To make more ports visible outside the container consult EXPOSE statements in Dockerfile.

## Exeternally available web services :
```
http://localhost:8000		splunk (wouldn't have any other way!)
http://localhost:50070	   	Hadoop (yarn)
http://localhost:9090		Apache Nifi
http://localhost:8088		Hadoop
```

## Credits:
The following inviduals from Splunk for creating this tutorial and configuring splunk
```
Rannan Dagan
Scott Haskell
```
## Finally:
If like to build the image from scratch you can use my script clean_start.sh. Please be aware once the image is created locally it will not pull it from my hub repositoy (splunknbox). To do that you must manually delete your created image (docker rmi splunk_datafabric).

stay tune for more details...


