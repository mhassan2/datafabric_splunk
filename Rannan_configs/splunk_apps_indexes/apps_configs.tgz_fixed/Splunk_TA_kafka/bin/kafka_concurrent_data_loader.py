import threading
import Queue
from multiprocessing import Manager
from multiprocessing import Process
import os

import splunktalib.event_writer as ew
import splunktalib.timer_queue as tq
import splunktalib.orphan_process_monitor as opm
from splunktalib.common import log
from splunktalib.common import util as scutil

import kafka_data_loader as kdl
import kafka_consts as c

logger = log.Logs().get_logger("main")


def use_single_instance():
    res = scutil.is_true(os.environ.get("kafka_single_instance", "true"))
    return "{}".format(res).lower()


def _wait_for_tear_down(tear_down_q, loader):
    checker = opm.OrphanProcessChecker()
    while 1:
        try:
            go_exit = tear_down_q.get(block=True, timeout=2)
        except Queue.Empty:
            go_exit = checker.is_orphan()
            if go_exit:
                logger.info("%s becomes orphan, going to exit", os.getpid())

        if go_exit:
            break

    if loader is not None:
        loader.stop()
    logger.info("End of waiting for tear down signal")


def _load_data(tear_down_q, task_config):
    loader = kdl.KafkaDataLoader(task_config)
    thr = threading.Thread(
        target=_wait_for_tear_down, args=(tear_down_q, loader))
    thr.daemon = True
    thr.start()
    loader.index_data()
    thr.join()
    logger.info("End of load data")


class KafkaConcurrentDataLoader(object):

    def __init__(self, task_config, tear_down_q, process_safe):
        if process_safe:
            self._worker = Process(
                target=_load_data, args=(tear_down_q, task_config))
        else:
            self._worker = threading.Thread(target=_load_data,
                                            args=(tear_down_q, task_config))

        self._worker.daemon = True
        self._started = False
        self._tear_down_q = tear_down_q
        self.name = task_config[c.name]

    def start(self):
        if self._started:
            return
        self._started = True

        self._worker.start()
        logger.info("Kafka concurrent data loader started.")

    def stop(self):
        if not self._started:
            return
        self._started = False

        self._tear_down_q.put(True)
        logger.info("Kafka concurrent data loader is going to exit.")


class KafkaDataLoaderManager(object):

    def __init__(self, task_configs):
        self._task_configs = task_configs
        self._wakeup_queue = Queue.Queue()
        self._timer_queue = tq.TimerQueue()
        self._mgr = None
        self._started = False
        self._stop_signaled = False

    def start(self):
        if self._started:
            return
        self._started = True

        self._timer_queue.start()

        process_safe = self._use_multiprocess()
        logger.info("Use multiprocessing=%s", process_safe)

        event_writer = ew.EventWriter(process_safe=process_safe)
        event_writer.start()

        tear_down_q = self._create_tear_down_queue(process_safe)

        loaders = []
        for task in self._task_configs:
            task[c.data_loader] = event_writer
            loader = KafkaConcurrentDataLoader(task, tear_down_q, process_safe)
            loader.start()
            loaders.append(loader)

        logger.info("KafkaDataLoaderManager started")
        _wait_for_tear_down(self._wakeup_queue, None)
        logger.info("KafkaDataLoaderManager got stop signal")

        for loader in loaders:
            logger.info("Notify loader=%s", loader.name)
            loader.stop()

        event_writer.tear_down()
        self._timer_queue.tear_down()

        if self._mgr is not None:
            self._mgr.shutdown()

        logger.info("KafkaDataLoaderManager stopped")

    def stop(self):
        self._stop_signaled = True
        self._wakeup_queue.put(True)
        logger.info("KafkaDataLoaderManager is going to stop.")

    def stopped(self):
        return not self._started

    def received_stop_signal(self):
        return self._stop_signaled

    def add_timer(self, callback, when, interval):
        return self._timer_queue.add_timer(callback, when, interval)

    def remove_timer(self, timer):
        self._timer_queue.remove_timer(timer)

    def _use_multiprocess(self):
        if not self._task_configs:
            return False

        single_instance = use_single_instance()
        use_process = self._task_configs[0].get(c.use_multiprocess_consumer)
        return (scutil.is_true(single_instance) and
                len(self._task_configs) > 1 and
                scutil.is_true(use_process))

    def _create_tear_down_queue(self, process_safe):
        if process_safe:
            self._mgr = Manager()
            tear_down_q = self._mgr.Queue()
        else:
            tear_down_q = Queue.Queue()
        return tear_down_q


if __name__ == "__main__":
    import copy
    import time

    config = {
        c.name: "mytest",
        c.kafka_brokers: "172.16.107.153:9092",
        c.kafka_topic: [["test", None, -2]],
        c.kafka_partition_offset: -2,
        c.use_kv_store: False,
        c.appname: "Splunk_TA_kafka",
        c.index: "main",
        c.checkpoint_dir: ".",
        c.server_uri: "https://localhost:8089",
        c.server_host: "localhost",
        c.kafka_partition: 1,
        c.use_multiprocess_consumer: 1,
    }

    task_configs = []
    for i in range(1):
        cp_config = copy.deepcopy(config)
        cp_config[c.kafka_topic][0][1] = i
        task_configs.append(cp_config)
    config[c.kafka_topic][0] = ["test_topic", -2]
    task_configs.append(config)

    l = KafkaDataLoaderManager(task_configs)

    def _tear_down():
        time.sleep(30)
        l.stop()

    threading.Thread(target=_tear_down).start()
    l.start()
