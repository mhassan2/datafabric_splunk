#!/usr/bin/env bash

# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


#--------------------------------------------------------------
#Modified by MyH for this container:
clear
scriptNAME="${0##*/}"
parentID=$(ps -o ppid= $$)
parentNAME=`ps -f $parentID|awk '{print $10}' | tr '\n' ' '| sed 's/ //g'`
echo "[$parentNAME]"
if [ -z "$parentNAME" ]; then
printf "\033[1;34mThis [$scriptNAME] is the official method to start Yarn. While you can still use this script, it is recommend that you use \033[0;32m/etc/init.d/yarn [start|stop|restart]\033[0m \033[1;34m warpper script instead. All startup scritps in /etc/init.d has been modified to work with this container. "
printf "\033[1;34mIf you continue to use; some non-critical operations may not work properly, like:\n-syncing with superisord (http://localhost:9001)\n-Preventing startup if ENV var set YARN=NO (by docker run)\033[m\n"
echo
read -p "<Enter> To continue using this script. <CTRL-C> to abort?" x
echo
fi
#--------------------------------------------------------------


# Start all yarn daemons.  Run this on master node.

echo "starting yarn daemons"

bin=`dirname "${BASH_SOURCE-$0}"`
bin=`cd "$bin"; pwd`

DEFAULT_LIBEXEC_DIR="$bin"/../libexec
HADOOP_LIBEXEC_DIR=${HADOOP_LIBEXEC_DIR:-$DEFAULT_LIBEXEC_DIR}
. $HADOOP_LIBEXEC_DIR/yarn-config.sh

# start resourceManager
"$bin"/yarn-daemon.sh --config $YARN_CONF_DIR  start resourcemanager
# start nodeManager
"$bin"/yarn-daemons.sh --config $YARN_CONF_DIR  start nodemanager
# start proxyserver
#"$bin"/yarn-daemon.sh --config $YARN_CONF_DIR  start proxyserver
