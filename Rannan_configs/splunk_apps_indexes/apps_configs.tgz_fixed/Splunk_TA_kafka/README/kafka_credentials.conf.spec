[<name>]
kafka_brokers = Kakfa broker list separated by ",", for example 172.16.107.153:9092,172.16.107.154:9092,172.16.107.155:9092
kafka_partition = topic partition list, separated by ",". For example, 0,1,2
kafka_partition_offset = earliest or latest
kafka_topic_blacklist = regex specifying topics to exclude from data collection
kafka_topic_whitelist = regex specifying topics to include in data collection
kafka_topic_group = topic group name, user can set this for best resource usage, refer to the AddOn's documentation for more details.
index = splunk index
removed = true/false, if set to true, this stanza will be marked as invalid and will be removed by the TA
