import Queue
import multiprocessing
import threading
import sys

from splunktalib.common import log

logger = log.Logs().get_logger("util")


class EventWriter(object):

    def __init__(self, process_safe=False):
        if process_safe:
            self._mgr = multiprocessing.Manager()
            self._event_queue = self._mgr.Queue(1000)
        else:
            self._event_queue = Queue.Queue(1000)
        self._event_writer = threading.Thread(target=self._do_write_events)
        self._started = False

    def start(self):
        if self._started:
            return
        self._started = True

        self._event_writer.start()
        logger.info("Event writer started.")

    def tear_down(self):
        if not self._started:
            return
        self._started = False

        self._event_queue.put(None)
        self._event_writer.join()
        logger.info("Event writer stopped.")

    def write_events(self, events):
        if events is None:
            return

        self._event_queue.put(events)

    def _do_write_events(self):
        event_queue = self._event_queue
        write = sys.stdout.write
        got_shutdown_signal = False

        while 1:
            try:
                event = event_queue.get(timeout=3)
            except Queue.Empty:
                # We need drain the queue before shutdown
                # timeout means empty for now
                if got_shutdown_signal:
                    logger.info("Event writer is going to exit...")
                    break
                else:
                    continue

            if event is not None:
                write(event)
            else:
                logger.info("Event writer got tear down signal")
                got_shutdown_signal = True
