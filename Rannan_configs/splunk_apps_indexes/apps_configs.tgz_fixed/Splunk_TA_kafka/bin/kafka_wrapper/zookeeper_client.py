import traceback
# Disable "No log handler issue"
import logging
logging.basicConfig()

from kazoo.client import KazooClient
from kazoo.retry import KazooRetry

import ta_util2.log as log
import kafka_consts as c

logger = log.Logs().get_logger("main")


class ZooKeeper(object):
    max_tries = 3
    max_delay = 4
    delay = 1

    def __init__(self, config):
        """
        @config: dict like object which contains:
        {
        "zookeepers": ip:port,ip2:port,
        }
        """

        self._config = config
        self._zk = KazooClient(hosts=config[c.zookeepers])
        self._started = False

    def start(self):
        if self._started:
            logger.info("ZookeeperClient has already started.")
            return
        self._started = True

        try:
            self._zk.start()
        except Exception:
            logger.error("Failed to start zookeeper client, error=%s",
                         traceback.format_exc())
            raise

        logger.info("ZookeeperClient started...")

    def stop(self):
        if not self._started:
            logger.info("ZookeeperClient has already stopped.")
            return
        self._started = False

        self._zk.stop()

    def election(self, election_path, identifier=None, callback=None):
        """
        @election_path: zookeeper node path of election
        @identifier: identifiy the candidates
        @return: block until the caller is the leader, callback will be invoked
        """

        election = self._zk.Election(election_path, identifier)
        election.run(callback)

    def create(self, path, value="", ephemeral=False,
               sequence=False, makepath=False):
        retry = KazooRetry(max_tries=self.max_tries, delay=self.delay,
                           max_delay=self.max_delay, ignore_expire=False)
        return retry(self._zk.create, path=path, value=value,
                     ephemeral=ephemeral, sequence=sequence, makepath=makepath)

    def ensure_path(self, path):
        retry = KazooRetry(max_tries=self.max_tries, delay=self.delay,
                           max_delay=self.max_delay, ignore_expire=False)
        return retry(self._zk.ensure_path, path)

    def get(self, path, watch=None):
        retry = KazooRetry(max_tries=self.max_tries, delay=self.delay,
                           max_delay=self.max_delay, ignore_expire=False)
        return retry(self._zk.get, path, watch)

    def get_children(self, path, watch=None):
        retry = KazooRetry(max_tries=self.max_tries, delay=self.delay,
                           max_delay=self.max_delay, ignore_expire=False)
        return retry(self._zk.get_children, path, watch)

    def exists(self, path, watch=None):
        # retry = KazooRetry(max_tries=self.max_tries, delay=self.delay,
        #                    max_delay=self.max_delay, ignore_expire=False)
        # return retry(self._zk.exists, path, watch)
        return self._zk.exists(path, watch)

    def set(self, path, value):
        retry = KazooRetry(max_tries=self.max_tries, delay=self.delay,
                           max_delay=self.max_delay, ignore_expire=False)
        return retry(self._zk.set, path, value)

    def delete(self, path, recursive=False):
        retry = KazooRetry(max_tries=self.max_tries, delay=self.delay,
                           max_delay=self.max_delay, ignore_expire=False)
        return retry(self._zk.delete, path, recursive=recursive)
