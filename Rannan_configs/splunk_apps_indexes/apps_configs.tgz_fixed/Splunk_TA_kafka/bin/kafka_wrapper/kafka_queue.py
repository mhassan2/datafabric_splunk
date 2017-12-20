import time
import traceback

# Disable "No log handler for xxx" issue
import logging
logging.basicConfig()

import kafka

from splunktalib.common import log
import kafka_consts as c

logger = log.Logs().get_logger("main")


def get_kafka_client(config):
    for i in range(3):
        try:
            return kafka.KafkaClient(config[c.kafka_brokers])
        except kafka.common.KafkaUnavailableError as e:
            last_exception = e
            logger.error("Failed to create kafka client, this is usually due "
                         "to all of the brokers died or invalid broker "
                         "IP/ports, error=%s", traceback.format_exc())
            time.sleep(i + 1)
        except Exception as e:
            last_exception = e
            logger.error("Failed to create kafka client, error=%s",
                         traceback.format_exc())
            time.sleep(i + 1)
    raise last_exception


class KafkaQueue(object):

    max_try = 3
    backoff = 2
    smallest = -2
    largest = -1

    roundrobin_partitioner = "roundrobin"
    hash_partitioner = "hashed"

    def __init__(self, config):
        """
        @config: dict like object which contains the following key/values
        {
        "role": "producer", or "consumer" or "producer_and_consumer",
        "kafka_brokers": "ip1:port1,ip2:port2,ip3:port3",
        producer_config: {
            "partitioner_type": "hashed or roundrobin",
        },
        consumer_config: {
            "topic": {(topic, partition?): offset, ...}
            "group_id": consumer group_id,
            "consumer_timeout_ms": timeout before available data,
            "fetch_message_max_bytes": 1024 * 1024
        }
        }
        """

        # FIXME more options like sync producer or async producer

        assert config and config.get(c.kafka_brokers)

        self._config = config
        self._client = get_kafka_client(config)
        self._create_producer()
        self._create_consumer()
        self._started = True

    def _create_producer(self):
        role = self._config.get("role", "producer_and_consumer")
        if "producer" not in role:
            return

        producer_config = self._config.get("producer_config", {})
        partitioner_type = producer_config.get("partitioner_type")
        if partitioner_type == self.hash_partitioner:
            producer = kafka.KeyedProducer(
                self._client, partitioner=kafka.HashedPartitioner)
            self._producer_type = "keyed"
        elif partitioner_type == self.roundrobin_partitioner:
            producer = kafka.KeyedProducer(
                self._client, partitioner=kafka.RoundRobinPartitioner)
            self._producer_type = "keyed"
        else:
            producer = kafka.SimpleProducer(self._client)
            self._producer_type = "simple"

        self._producer = producer

    def _set_partition_offsets(self, consumer_config):
        topic = consumer_config[c.kafka_topic]
        assert isinstance(topic, dict)

        partition_offsets = {}
        for topic_partition, offset in topic.iteritems():
            assert isinstance(topic_partition, tuple)
            if len(topic_partition) == 2:
                real_offset = self._get_real_offset(
                    topic_partition[0], topic_partition[1], offset)
                partition_offsets[topic_partition] = real_offset
            else:
                partitions = self._client.get_partition_ids_for_topic(
                    topic_partition[0])
                for partition in partitions:
                    real_offset = self._get_real_offset(
                        topic_partition[0], partition, offset)
                    topic_part = (topic_partition[0], partition)
                    partition_offsets[topic_part] = real_offset

        if not partition_offsets:
            return
        self._consumer.set_topic_partitions(partition_offsets)

    def _get_real_offset(self, topic, partition, offset):
        begin_or_end = offset
        if offset > self.largest:
            # clients want an offset: smallest + offset
            begin_or_end = self.smallest
        elif offset < self.smallest:
            # clients want an offset: largest - offset
            begin_or_end = self.largest

        offsets = self._consumer.get_partition_offsets(
            topic, partition, begin_or_end, 10)

        if offset > self.largest or offset < self.smallest:
            offset = offset + offsets[0]
        else:
            offset = offsets[0]
        return offset

    def _create_consumer(self):
        role = self._config.get("role", "producer_and_consumer")
        if "consume" not in role:
            return

        consumer_config = self._config.get("consumer_config", {})
        assert consumer_config.get(c.kafka_topic)

        consumer = kafka.KafkaConsumer(
            group_id=consumer_config.get("group_id"),
            bootstrap_servers=self._config[c.kafka_brokers],
            consumer_timeout_ms=consumer_config.get("consumer_timeout_ms", -1),
            fetch_message_max_bytes=consumer_config.get("fetch_message_max_bytes"),
            auto_commit_enable=False, auto_offset_reset="largest")
        self._consumer = consumer
        self._set_partition_offsets(consumer_config)

    def start(self):
        pass

    def stop(self):
        if self._started:
            self._client.close()
        self._started = False

    def put(self, meta_data, msg):
        """
        @meta_data: dict like object contains
        {
        "topic": kafka_topic_name,
        "key": message key, # for keyed producer
        }
        @msg: str
        """

        assert meta_data and meta_data.get(c.kafka_topic)

        for i in range(self.max_try):
            try:
                if self._producer_type == "simple":
                    return self._producer.send_messages(
                        meta_data[c.kafka_topic], msg)
                else:
                    assert "key" in meta_data
                    return self._producer.send(
                        meta_data[c.kafka_topic], meta_data["key"], msg)
            except kafka.common.LeaderNotAvailableError as e:
                last_exception = e
            except Exception as e:
                last_exception = e
                logger.error("Failed to write message, error=%s",
                             traceback.format_exc())
            time.sleep((i + 1) * self.backoff)
        raise last_exception

    def get(self, meta_data=None):
        for i in range(self.max_try):
            try:
                return self._consumer.next()
            except kafka.common.ConsumerTimeout:
                return None
            except Exception as e:
                last_exception = e
                logger.error("Failed to get consume message, error=%s",
                             traceback.format_exc())
            time.sleep((i + 1) * self.backoff)
        raise last_exception

    def get_client(self):
        return self._client

    def commit(self, msgs):
        for msg in msgs:
            self._consumer.task_done(msg)

        for i in range(self.max_try):
            try:
                self._consumer.commit()
            except Exception as e:
                logger.error("Failed to commit messages, error=%s",
                             traceback.format_exc())
                last_exception = e
                time.sleep((i + 1) * self.backoff)
        raise last_exception


def create_producer_q(config):
    kafka_config = {
        "role": "producer",
        c.kafka_brokers: config[c.kafka_brokers],
    }
    return KafkaQueue(kafka_config)


def create_consumer_q(config, topic, partition=None, group_id=None,
                      offset=KafkaQueue.largest, max_bytes=1024*1024):
    if isinstance(topic, dict):
        t = topic
    elif partition is not None:
        t = {(topic, partition): offset}
    else:
        t = {(topic,): offset}

    kafka_config = {
        "role": "consumer",
        c.kafka_brokers: config[c.kafka_brokers],
        "consumer_config": {
            c.kafka_topic: t,
            "group_id": group_id,
            "consumer_timeout_ms": 6 * 1000,
            "fetch_message_max_bytes": max_bytes,
        }
    }
    return KafkaQueue(kafka_config)
