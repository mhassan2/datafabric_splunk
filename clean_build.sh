#!/bin/bash
uname=`uname -a | awk '{print $1}'`
CONTAINER="DF01"
IMAGE="splunknbox/splunk_datafabric"

#--------------------------------------------------------
function osx_say(){
VOL_LEVEL=7
string=$1
printf "\033[1;32m$string\033[0m\n"
if [ "$(uname)" == "Darwin" ]; then
	say "[[volm 0.$((RANDOM%$VOL_LEVEL+1))]] $string"
fi

}
#--------------------------------------------------------

osx_say "Deleteing $CONTAINER container"
docker rm -f $CONTAINER

osx_say "Deleting $IMAGE image..."
docker rmi $IMAGE

osx_say "Deleting all volumes..."
docker volume rm $(docker volume ls -qf 'dangling=true')

echo; echo
osx_say "Building $IMAGE image, [15 minutes]..."
cd ~/datafabric_splunk
time docker build --no-cache=true -f Dockerfile -t $IMAGE .

echo;echo
osx_say "Creating $CONTAINER container. Enter to continue.."
read -p "<Enter> to continue creating container. <CTRL-C> to abort?" x
#time docker run -d --name=$CONTAINER --hostname=$CONTAINER -p 2122:22 -p 8000:8000 -p 8088:8088 -p 9090:9090 -p 50070:50070 -p 8042:8042 -p 19888:19888 -e NIFI="NO" -e KAFKA="NO" -e ZK="NO" $IMAGE

time docker run -d --name=$CONTAINER --hostname=$CONTAINER -p 2122:22 -p 8000:8000 -p 8088:8088 -p 8188:8188 -p 10020:10020 -p 9001:9001 -p 9090:9090 -p 50070:50070  $IMAGE

osx_say "We are done, baby"
echo "-------------------------  We are done baby! ------------------------"

printf "\033[1;37m Current images:\033[0m\n" docker images
printf "\033[1;37m Current container:\033[0m]\n"; docker ps -a

#must be logged in splunknbox repo
osx_say "Ready to push image to docker hub. [2 hours]. Enter to abort"
read -p "Are you sure you want to proceed? [y/N]? " answer
if [ "$answer" == "y" ] || [ "$answer" == "Y" ]; then
	time docker push $IMAGE
fi

