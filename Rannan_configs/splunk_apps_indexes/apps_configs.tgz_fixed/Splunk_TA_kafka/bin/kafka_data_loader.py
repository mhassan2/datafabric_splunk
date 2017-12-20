import traceback
import time
from base64 import b64encode

import splunktalib.state_store as ss
import splunktalib.common.util as scutil
from splunktalib.common import log
import kafka_consts as c
import kafka_wrapper.kafka_queue as kq

logger = log.Logs().get_logger("main")


class KafkaDataLoader(object):

    def __init__(self, task_config):
        """
        :task_config: dict object
        {
            "kafka_topic": [[<topic_info>], ...]
            # <topic_info>: [topic_name, partition, offset, index] or
            #               [topic_name, offset, index]
        }

        """

        self._idx_tbl = self._build_index_lookup_tbl(task_config)
        logger.debug("index table=%s", self._idx_tbl)
        self._task_config = task_config
        max_bytes = self._task_config.get(c.fetch_message_max_bytes)
        try:
            max_bytes = int(max_bytes)
        except ValueError:
            max_bytes = 1024 * 1024
        self._task_config[c.fetch_message_max_bytes] = max_bytes

        self._running = False
        self._stopped = False
        self._store = ss.get_state_store(
            task_config, task_config[c.appname],
            use_kv_store=task_config.get(c.use_kv_store, False))
        self._brokers = b64encode(self._task_config[c.kafka_brokers])

    @staticmethod
    def _build_index_lookup_tbl(task_config):
        topics = task_config[c.kafka_topic]
        idx_tbl = {}
        for topic_info in topics:
            if isinstance(topic_info[-1], (str, unicode)):
                idx_tbl[topic_info[0]] = topic_info[-1]
                del topic_info[-1]
            else:
                idx_tbl[topic_info[0]] = task_config[c.index]
        return idx_tbl

    def get_interval(self):
        return 0

    def stop(self):
        self._stopped = True
        logger.info("Stopping KafkaDataLoader")

    def _get_topic_string(self):
        all_topic_partitions = []
        for topic_partition in self._task_config[c.kafka_topic]:
            assert len(topic_partition) in (2, 3)
            if len(topic_partition) == 3:
                tp = "{}_{}".format(*topic_partition[:-1])
            elif len(topic_partition) == 2:
                tp = "{}".format(topic_partition[0])
            all_topic_partitions.append(tp)
        return ",".join(all_topic_partitions)

    def _pop_ckpt_caches(self, ckpts, topic, partition, offset):
        key = "{}_{}_{}".format(self._brokers, topic, partition)
        ckpt = self._store.get_state(key)
        if not ckpt:
            ckpt = {
                c.kafka_partition_offset: offset
            }

        ckpt[c.kafka_topic] = topic
        ckpt[c.kafka_partition] = partition
        ckpts[key] = ckpt

    def _get_ckpts(self):
        ckpts = {}
        client = None
        for topic_partition in self._task_config[c.kafka_topic]:
            if len(topic_partition) == 3:
                self._pop_ckpt_caches(ckpts, *topic_partition)
            elif len(topic_partition) == 2:
                if client is None:
                    logger.info("Get kafka client")
                    client = kq.get_kafka_client(self._task_config)

                if topic_partition[0] not in client.topic_partitions:
                    logger.error("topic=%s does not exists in kafka=%s",
                                 topic_partition[0],
                                 self._task_config[c.kafka_cluster])
                    continue

                for partition in client.topic_partitions[topic_partition[0]]:
                    self._pop_ckpt_caches(ckpts, topic_partition[0], partition,
                                          topic_partition[1])
        return ckpts

    def __call__(self):
        self.index_data()

    @staticmethod
    def _build_partition_offsets(ckpts):
        partition_offsets = {}
        for v in ckpts.itervalues():
            k = (str(v[c.kafka_topic]), v[c.kafka_partition])
            offset = v[c.kafka_partition_offset]
            if offset >= 0:
                partition_offsets[k] = offset + 1
            else:
                partition_offsets[k] = offset
        return partition_offsets

    def _create_kafka_consumer(self, ckpts):
        partition_offsets = self._build_partition_offsets(ckpts)
        q = kq.create_consumer_q(
            self._task_config, partition_offsets,
            max_bytes=self._task_config[c.fetch_message_max_bytes])
        logger.info("Set offsets=%s", partition_offsets)
        return q

    def index_data(self):
        if self._running:
            return
        self._running = True

        logger.info("Start indexing data for %s", self._get_topic_string())
        while not self._stopped:
            try:
                self._do_safe_index()
            except Exception:
                logger.error("Failed to index data, reason=%s",
                             traceback.format_exc())
                time.sleep(2)
                continue
            break
        logger.info("End of indexing data for %s", self._get_topic_string())

    def _write_events(self, events, ckpts):
        loader = self._task_config[c.data_loader]
        brokers = self._task_config[c.kafka_brokers]

        evt_fmt = ("<event><host>{0}</host><source>{1}</source>"
                   "<sourcetype>kafka:topicEvent</sourcetype>"
                   "<index>{2}</index><data>{3}</data></event>")

        evts = (evt_fmt.format(
            brokers, "kafka:{}:{}".format(msg.topic, msg.partition),
            self._idx_tbl[msg.topic], scutil.escape_cdata(msg.value))
            for msg in events)
        loader.write_events("<stream>{}</stream>".format("".join(evts)))
        del events[:]

        while 1:
            for key, ckpt in ckpts.iteritems():
                try:
                    self._store.update_state(key, ckpt)
                except Exception:
                    time.sleep(2)
                    logger.error("Failed to update ckpt for key=%s reason=%s",
                                 key, traceback.format_exc())
                    continue
            return

    def _report_offsets(self, start_time, ckpts):
        # Every min, report the offsets
        now = time.time()
        if now - start_time >= 60:
            for ckpt in ckpts.itervalues():
                logger.info(
                    'brokers="%s" topic="%s" partition="%s" offset="%s"',
                    self._task_config[c.kafka_brokers],
                    ckpt[c.kafka_topic], ckpt[c.kafka_partition],
                    ckpt[c.kafka_partition_offset])
            return now
        return start_time

    def _do_safe_index(self):
        current_ckpts = self._get_ckpts()
        topic_string = self._get_topic_string()
        consumer = self._create_kafka_consumer(current_ckpts)
        write_events = self._write_events
        ltime = time.time
        report_offsets = self._report_offsets

        # 1) Cache max_events in memory before indexing for batch processing
        # 2) If there is max_count times which have no data, indexing whatever
        #    we have
        max_events, msgs = self._task_config.get(c.batch_count, 1000), []
        max_count, count = 10, 0

        # Report the data collection perf every 1M records
        current_record_count, record_report_threshhold = 0, 1000000
        record_report_start = ltime()
        offset_report_start = ltime()
        brokers = self._brokers

        while not self._stopped:
            try:
                msg = consumer.get()
            except Exception:
                msg = ("Failed to get msg from brokers={}, topic={}, "
                       "error={}").format(self._task_config[c.kafka_brokers],
                                          self._task_config[c.kafka_topic],
                                          traceback.format_exc())
                logger.error(msg)
                # Reconnect
                time.sleep(2)
                # FIXME invalid offset due to purge
                consumer = self._create_kafka_consumer(current_ckpts)
                continue

            if msg is not None:
                msgs.append(msg)
                key = "{}_{}_{}".format(brokers, msg.topic, msg.partition)
                current_ckpts[key][c.kafka_partition_offset] = msg.offset
            else:
                count += 1
                if count < max_count:
                    continue

            if len(msgs) >= max_events:
                current_record_count += len(msgs)
                if current_record_count >= record_report_threshhold:
                    logger.info("topic=%s, indexed=%s, time=%s",
                                topic_string, current_record_count,
                                time.time() - record_report_start)
                    record_report_start = ltime()
                    current_record_count = 0
                write_events(msgs, current_ckpts)
                offset_report_start = report_offsets(
                    offset_report_start, current_ckpts)
            elif count >= max_count:
                count = 0
                if msgs:
                    write_events(msgs, current_ckpts)
                    offset_report_start = report_offsets(
                        offset_report_start, current_ckpts)

        self._running = False


if __name__ == "__main__":
    import sys

    class O(object):

        def write_events(self, evt):
            sys.stdout.write(evt)

    config = {
        c.name: "mytest",
        c.kafka_cluster: "local_kf",
        c.kafka_brokers: "172.16.107.153:9092",
        c.kafka_topic: [["small_records_topic", -2]],
        c.kafka_partition_offset: -2,
        c.use_kv_store: False,
        c.appname: "Splunk_TA_kafka",
        c.index: "main",
        c.data_loader: O(),
        c.checkpoint_dir: ".",
        c.server_uri: "https://localhost:8089",
        c.server_host: "localhost",
        c.kafka_partition: 1,
    }

    import cProfile
    import pstats
    import cStringIO

    pr = cProfile.Profile()
    pr.enable()

    loader = KafkaDataLoader(config)
    loader.index_data()

    pr.disable()
    s = cStringIO.StringIO()
    sortby = 'cumulative'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print s.getvalue()
