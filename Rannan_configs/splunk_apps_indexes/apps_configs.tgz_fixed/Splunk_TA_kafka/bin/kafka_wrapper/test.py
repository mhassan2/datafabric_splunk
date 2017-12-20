import logging
logging.basicConfig()

import kafka_queue as kq
import threading


global_topic = "small_records_topic"


def produce():
    config = {
        "role": "producer",
        "kafka_brokers": "172.16.107.153:9092",
        "producer_config": {
            "partitioner_type": "roundrobin",
        },
    }

    ts = []
    for i in xrange(3):
        ts.append(threading.Thread(target=produce_data, args=(config,)))
        ts[-1].start()

    for t in ts:
        t.join()


def produce_data(config):
    q = kq.KafkaQueue(config)
    meta = {
        "kafka_topic": global_topic,
        "key": 1,
    }

    lin = "Nov  8 03:45:45 hydra dbus-daemon: dbus[762]: [system] Activating via systemd: service name='org.freedesktop.nm_dispatcher' unit='dbus-org.freedesktop.nm-dispatcher.service'"
    for i in xrange(3300000):
        meta["key"] = str(int(meta["key"]) + 1)
        print q.put(meta, lin)


def consume():
    topic = {
        (global_topic, 0): kq.KafkaQueue.smallest,
        (global_topic, 1): kq.KafkaQueue.smallest,
        (global_topic, 2): kq.KafkaQueue.smallest,
    }

    topic = {
        (global_topic,): kq.KafkaQueue.smallest,
    }
    config = {
        "role": "consumer",
        "kafka_brokers": "172.16.107.153:9092",
        "consumer_config": {
            "kafka_topic": topic,
            "consumer_timeout_ms": 30000,
        },
    }
    q = kq.KafkaQueue(config)
    for i in xrange(10000):
        msg = q.get()
        if msg is not None:
            print msg.topic, msg.partition, msg.offset


def main():
    # kc = kq.get_kafka_client(config)
    # kc.load_metadata_for_topics()
    # print kc.topic_partitions
    produce()
    # consume()


if __name__ == "__main__":
    main()
