import re
import traceback
import json
import socket
import copy
from contextlib import contextmanager
import itertools
import random
import time
import multiprocessing
from base64 import b64encode

import splunktalib.modinput as modinput
import splunktalib.conf_manager.ta_conf_manager as tcm
import splunktalib.conf_manager.conf_manager as cm
import splunktalib.conf_manager.request as req
import splunktalib.credentials as cred
import splunktalib.state_store as ss
import splunktalib.splunk_cluster as sc
import splunktalib.rest as rest
import splunktalib.common.util as utils
from splunktalib.common import log

import kafka_concurrent_data_loader as kcdl
import kafka_wrapper.kafka_queue as kq
import kafka_consts as c
import kafka_load_policy as klp


logger = log.Logs().get_logger("main")


def create_kafka_config():
    meta_configs, stanza_configs = modinput.get_modinput_configs_from_stdin()
    return KafkaConfig(meta_configs, stanza_configs)


def _use_kv_store(server_info):
    # Only when release >= 6.2, in SHC, use global KV store
    if server_info.version() < "6.2":
        return False

    if server_info.is_shc_member():
        return True

    return False


def create_state_store(meta_configs, appname, server_info):
    if _use_kv_store(server_info):
        store = ss.get_state_store(
            meta_configs, appname, appname.lower(),
            use_kv_store=True)
        logger.info("Use KVStore to do ckpt")
    else:
        store = ss.get_state_store(meta_configs, appname)
    return store


def setup_signal_handler(data_loader, kconfig):
    """
    Setup signal handlers
    :data_loader: data_loader.DataLoader instance
    """

    def _handle_exit(signum, frame):
        if kconfig is not None:
            logger.info("Remove file lock")
            store = ss.get_state_store(kconfig._meta_configs, kconfig._appname)
            store.delete_state(FileLock.lock_key)

        logger.info("%s TA is going to exit...", c.ta_name)

        if data_loader is not None:
            data_loader.stop()

    utils.handle_tear_down_signals(_handle_exit)


def extract_hostname_port(uri):
    assert uri

    hostname, port = None, None

    if uri.startswith("https://"):
        uri = uri[8:]
    elif uri.startswith("http://"):
        uri = uri[7:]

    m = re.search(r"([^/:]+):(\d+)", uri)
    if m:
        hostname = m.group(1)
        port = m.group(2)
    return hostname, port


@contextmanager
def save_and_restore(stanza, keys, exceptions=()):
    vals = [stanza.get(key) for key in keys]
    yield
    for key, val in itertools.izip(keys, vals):
        if (key, val) not in exceptions:
            stanza[key] = val


class FileLock(object):
    lock_key = "ckpt.lock"

    def __init__(self, meta_configs, appname):
        self._locked = False

        random.seed(time.time())
        time.sleep(random.uniform(1, 3))

        self._store = ss.get_state_store(meta_configs, appname)
        while 1:
            state = self._store.get_state(self.lock_key)
            if not state or time.time() - state["time"] > 300:
                state = {
                    "pid": multiprocessing.current_process().ident,
                    "time": time.time(),
                }
                # grap it
                self._store.update_state(self.lock_key, state)
                self._locked = True
                logger.info("Grapped ckpt.lock")
                break
            else:
                logger.debug("Ckpt lock is held by other mod process")
                time.sleep(1)

    def locked(self):
        return self._locked

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._locked:
            self._store.delete_state(self.lock_key)
            logger.info("Removed ckpt.lock")


# FIXME refactoring KafkaConfig

class KafkaConfig(object):
    _appname = c.kafka_ta_name
    _current_hostname = socket.gethostname()
    _current_addrs = []
    try:
        _current_addrs = socket.gethostbyname_ex(_current_hostname)
    except Exception:
        pass
    _current_hostname = _current_hostname.lower()

    def __init__(self, meta_configs, stanza_configs):
        self._meta_configs = meta_configs
        self._stanza_configs = stanza_configs
        self._task_configs = []
        self._kafka_topics = None
        self._server_info = sc.ServerInfo(self._meta_configs[c.server_uri],
                                          self._meta_configs[c.session_key])
        setup_signal_handler(None, self)
        self._dispatch_errors = None
        self._servername, self._port = extract_hostname_port(
            self._meta_configs[c.server_uri])

        self._store = create_state_store(
            self._meta_configs, self._appname, self._server_info)

        conf_mgr = cm.ConfManager(self._meta_configs[c.server_uri],
                                  self._meta_configs[c.session_key])

        global_settings = conf_mgr.all_stanzas_as_dicts(
            c.myta_conf, do_reload=True)
        kafka_clusters = self._get_kafka_clusters(conf_mgr, global_settings)

        log.Logs().set_level(
            global_settings[c.global_settings].get(c.log_level, "INFO"))
        if kafka_clusters:
            self._retry_dispatch_tasks(global_settings, kafka_clusters)
            # Refresh kafka clusters
            kafka_clusters = self._get_kafka_clusters(
                conf_mgr, global_settings)
            self._kafka_clusters = kafka_clusters
            self._get_task_configs(global_settings, kafka_clusters)
        else:
            logger.info("No Kafka cluster are configured")

    def get_task_configs(self):
        return self._task_configs

    def get_meta_configs(self):
        return self._meta_configs

    def topics_changed(self):
        try:
            new_topics = self._get_topics(self._kafka_clusters)
        except Exception:
            logger.error("Failed to get topics, error=%s",
                         traceback.format_exc())
            return False

        for k, v in new_topics.iteritems():
            if k not in self._kafka_topics:
                return True

            if v[c.kafka_topic] != self._kafka_topics[k][c.kafka_topic]:
                return True
        return False

    def _get_kafka_clusters(self, conf_mgr, global_settings):
        kafka_clusters = conf_mgr.all_stanzas_as_dicts(
            c.myta_cred_conf, do_reload=True)
        kafka_clusters = {
            k: v for k, v in kafka_clusters.iteritems()
            if v.get(c.kafka_brokers) is not None
        }

        index = global_settings[c.global_settings].get(c.index)
        if not index:
            return kafka_clusters

        for cluster in kafka_clusters.itervalues():
            if not cluster.get(c.index):
                cluster[c.index] = index
        return kafka_clusters

    def _retry_dispatch_tasks(self, global_settings, kafka_clusters):
        for i in range(3):
            self._dispatch_tasks(global_settings, kafka_clusters)
            if self._dispatch_errors:
                logger.warn("Error happened for task dispatching, retrying")
                time.sleep(2 ** (i + 1))
                continue
            else:
                break

    def _dispatch_tasks(self, global_settings, kafka_clusters):
        conf_mgr = tcm.TAConfManager(
            c.myta_forwarder_conf, self._meta_configs[c.server_uri],
            self._meta_configs[c.session_key], appname=self._appname)
        conf_mgr.reload()
        forwarders = conf_mgr.all(return_acl=False)
        if not self.is_dispatcher(self._server_info, forwarders):
            return

        lock = FileLock(self._meta_configs, self._appname)
        if not lock.locked():
            return

        with lock:
            self._do_dispatch(global_settings, kafka_clusters,
                              forwarders, conf_mgr)

    def is_dispatcher(self, server_info=None, forwarders=None):
        if not forwarders:
            conf_mgr = tcm.TAConfManager(
                c.myta_forwarder_conf, self._meta_configs[c.server_uri],
                self._meta_configs[c.session_key], appname=self._appname)
            forwarders = conf_mgr.all(return_acl=False)

        if not forwarders:
            return False

        if not server_info:
            server_info = sc.ServerInfo(self._meta_configs[c.server_uri],
                                        self._meta_configs[c.session_key])

        if server_info.is_shc_member():
            # In SHC env, only captain is able to dispatch the tasks
            if not server_info.is_captain():
                logger.info("This SH is not captain, ignore task dispatching")
                return False
        return True

    def _do_dispatch(self, global_settings, kafka_clusters,
                     forwarders, conf_mgr):
        # When forarders have been configured in this instance, it acts
        # a configuration/task dispatcher
        conf_mgr.set_encrypt_keys((c.username, c.password))
        for f in forwarders.itervalues():
            if not conf_mgr.is_encrypted(f):
                conf_mgr.update(f)

        forwarders = conf_mgr.all(return_acl=False)
        failed = self._dispatch_tasks_to_forwarders(
            global_settings, kafka_clusters, forwarders)
        if not failed:
            # Only when there are no failure, delete "removed" forwarders
            self._remove_forwarders(forwarders, conf_mgr)

    def _get_task_configs(self, global_settings, kafka_clusters):
        lock = FileLock(self._meta_configs, self._appname)
        if lock.locked():
            with lock:
                self._remove_tasks(kafka_clusters, global_settings)

        if not self._stanza_configs:
            logger.info("No data inputs are enabled")
            return

        task_configs = self._merge_global_settings(
            global_settings, kafka_clusters)

        if kcdl.use_single_instance() == "true":
            task_configs = klp.expand_or_merge_tasks(
                task_configs, kafka_clusters)
        self._task_configs = task_configs

    def _merge_global_settings(self, global_settings, kafka_clusters):
        task_configs = []
        keys = [c.index, c.name, c.kafka_partition_offset, c.kafka_partition,
                c.kafka_topic_group]
        kafka_clients = {}
        for stanza in self._stanza_configs:
            with save_and_restore(stanza, keys):
                valid_kafka = utils.is_false(
                    kafka_clusters[stanza[c.kafka_cluster]].get(c.removed))
                if not valid_kafka:
                    continue

                if stanza[c.kafka_cluster] not in kafka_clusters:
                    logger.warn("%s is refered by data input stanza %s, but "
                                "it is not found in kafka conf",
                                stanza[c.kafka_cluster], stanza[c.name])
                    continue

                stanza.update(global_settings[c.global_settings])
                stanza.update(kafka_clusters[stanza[c.kafka_cluster]])
                stanza.update(self._meta_configs)
                stanza[c.appname] = self._appname

            self._set_offset(stanza)
            # construct topic, partition list for KafkaDataLoader
            topic = stanza[c.kafka_topic]
            topic_parts = [[topic, stanza[c.kafka_partition_offset], stanza[c.index]]]
            partitions = self._filter_partitions(
                stanza, (topic,), kafka_clusters[stanza[c.kafka_cluster]],
                kafka_clients)
            if partitions:
                topic_parts = [
                    [topic, pid, stanza[c.kafka_partition_offset], stanza[c.index]]
                    for pid in partitions]
            stanza[c.kafka_topic] = topic_parts
            task_configs.append(stanza)
        return task_configs

    @staticmethod
    def get_partitions(stanza):
        partition_ids = []
        partitions = stanza.get(c.kafka_partition)
        if partitions:
            partitions = partitions.strip()
            for pid in partitions.split(","):
                try:
                    partition_ids.append(int(pid))
                except ValueError:
                    continue
        return partition_ids

    def _set_offset(self, stanza):
        offset = stanza.get(c.kafka_partition_offset)
        if offset == c.smallest:
            offset = kq.KafkaQueue.smallest
        else:
            offset = kq.KafkaQueue.largest
        stanza[c.kafka_partition_offset] = offset
        return stanza

    @staticmethod
    def _convert_to_new_ckpt_schema(dispatched_tasks, global_settings):
        if not dispatched_tasks:
            return {}

        index = global_settings[c.global_settings].get(c.index, "default")
        for forwarder_tasks in dispatched_tasks.itervalues():
            for task in forwarder_tasks.itervalues():
                for i, topic in enumerate(task[c.kafka_topic]):
                    if isinstance(topic, str):
                        # old ckpt schema
                        task[c.kafka_topic][i] = [topic, None, None, index]
        return dispatched_tasks

    def _dispatch_tasks_to_forwarders(self, global_settings, kafka_clusters,
                                      forwarders):
        """
        dispatched task ckpt is json object like
        {
            "kafka_cluster_stanza_name": {
                "forwarder_stanza_name": {
                    "brokers": [brokers],
                    "kafka_topic": [topic, ...], old schema, or
                    "kafka_topic": [[topic, partitions, topic_group, index],...],
                },
                "forwarder_stanza_name2": {
                    "brokers": [brokers],
                    "kafka_topic": [topic, ...], or
                    "kafka_topic": [[topic, partitions, topic_group, index],...],
                },
            },
        }
        """

        dispatched_tasks = self._store.get_state(c.dispatched_task_ckpt)
        dispatched_tasks = self._convert_to_new_ckpt_schema(
            dispatched_tasks, global_settings)
        logger.debug("existing dispathed_tasks=%s", dispatched_tasks)
        kafka_topics = self._get_topics(kafka_clusters)
        self._kafka_topics = copy.deepcopy(kafka_topics)

        failed = self._disable_tasks_on_forwarders(
            global_settings, kafka_clusters, forwarders,
            dispatched_tasks, kafka_topics)
        self._store.update_state(c.dispatched_task_ckpt, dispatched_tasks)

        forwarders = self._filter_out_removed(forwarders)
        kafka_clusters = self._filter_out_removed(kafka_clusters)
        task_assignments = klp.get_task_assignments(
            kafka_clusters, forwarders, kafka_topics, dispatched_tasks)
        self._do_dispatch_tasks(task_assignments, dispatched_tasks,
                                global_settings, kafka_clusters, forwarders)
        self._store.update_state(c.dispatched_task_ckpt, dispatched_tasks)
        logger.debug("new dispathed_tasks=%s", dispatched_tasks)

        if failed:
            self._dispatch_errors = True
        return failed

    @staticmethod
    def _filter_out_removed(kvs):
        return {
            k: v for k, v in kvs.iteritems()
            if utils.is_false(v.get(c.removed))
        }

    def _get_settings(self, global_settings_changed, global_settings):
        if global_settings_changed:
            return {
                "config_settings": {
                    c.global_settings: global_settings[c.global_settings],
                    c.credential_settings: {c.backend_update_req: True},
                    c.forwarder_credential_settings: c.ignore_backend_req,
                },
                "data_input_settings": {
                }
            }
        else:
            return {
                "config_settings": {
                    c.credential_settings: {c.backend_update_req: True},
                    c.forwarder_credential_settings: c.ignore_backend_req,
                },
                "data_input_settings": {
                },
            }

    @staticmethod
    def cleanup_settings(settings):
        deletes = (c.appname, c.user)
        for k in deletes:
            if k in settings:
                del settings[k]

    def _do_dispatch_tasks(self, task_assignments, dispatched_tasks,
                           global_settings, clusters, forwarders):
        """
        {
            global_settings: {},
            credential_settings: {},
        }
        """

        if not task_assignments:
            return

        self.cleanup_settings(global_settings[c.global_settings])
        gindex = global_settings[c.global_settings].get(c.index)

        forwarder_settings = {}
        for kafka_stanza, forwarder_tasks in task_assignments.iteritems():
            self.cleanup_settings(clusters[kafka_stanza])

            for forwarder_stanza, forwarder_task in forwarder_tasks.iteritems():
                if forwarder_stanza not in forwarder_settings:
                    forwarder_settings[forwarder_stanza] = \
                        self._get_settings(True, global_settings)
                fsettings = forwarder_settings[forwarder_stanza]
                config_settings = fsettings["config_settings"]
                config_settings[c.credential_settings][kafka_stanza] = \
                    clusters[kafka_stanza]
                data_input_settings = fsettings["data_input_settings"]
                for topic_partitions in forwarder_task[c.kafka_topic]:
                    index = clusters[kafka_stanza].get(c.index)
                    if not index:
                        if gindex:
                            index = gindex
                        else:
                            index = "main"

                    data_input_name = self._get_data_input_name(
                        kafka_stanza, topic_partitions[0])
                    data_input_settings[data_input_name] = {
                        c.kafka_cluster: kafka_stanza,
                        c.kafka_topic: topic_partitions[0],
                        c.kafka_partition: topic_partitions[1],
                        c.kafka_partition_offset: clusters[kafka_stanza][c.kafka_partition_offset],
                        c.kafka_topic_group: clusters[kafka_stanza].get(c.kafka_topic_group, ""),
                        c.index: index,
                    }
        self._send_request(clusters, forwarders, forwarder_settings,
                           dispatched_tasks)

    @staticmethod
    def _get_data_input_name(kafka_stanza, topic):
        return "{}_{}".format(kafka_stanza, topic)

    def _send_request(self, clusters, forwarders, forwarder_settings,
                      dispatched_tasks):
        settings_for_local = []
        for forwarder_stanza, settings in forwarder_settings.iteritems():
            forwarder = forwarders[forwarder_stanza]
            if self.is_current_host(forwarder[c.hostname]):
                settings_for_local.append((forwarder_stanza, settings))
                continue

            self._do_send(clusters, dispatched_tasks, forwarder_stanza,
                          forwarder, settings, localhost=False)

        # Handle local data input separately which caused TA to reboot
        logger.info("Handle local data inputs")
        for forwarder_stanza, settings in settings_for_local:
            forwarder = forwarders[forwarder_stanza]
            self._do_send(clusters, dispatched_tasks, forwarder_stanza,
                          forwarder, settings, localhost=True)

    def _do_send(self, clusters, dispatched_tasks, forwarder_stanza,
                 forwarder, settings, localhost=False):
        try:
            self._do_send_safe(clusters, dispatched_tasks, forwarder_stanza,
                               forwarder, settings, localhost)
        except Exception:
            self._dispatch_errors = True
            logger.error("Failed to dispatch task to forwarder %s, error=%s",
                         forwarder[c.hostname], traceback.format_exc())

    @staticmethod
    def _get_data_input_status(dispatched_tasks, forwarder_stanza,
                               datainput, datainput_name, conf_mgr):
        try:
            committed_di = conf_mgr.get_data_input(c.kafka_mod, datainput_name)
            committed_di = committed_di[0]
        except Exception:
            return "create"

        if ((not datainput[c.kafka_partition] and not committed_di.get(c.kafka_partition) or
             datainput[c.kafka_partition] == committed_di.get(c.kafka_partition))
                and (not datainput[c.index] and not committed_di.get(c.index) or
                     datainput[c.index] == committed_di.get(c.index))
                and (not datainput[c.kafka_topic_group] and not committed_di.get(c.kafka_topic_group) or
                     datainput[c.kafka_topic_group] == committed_di.get(c.kafka_topic_group))):
            return "update_ckpt"

        if datainput[c.kafka_cluster] not in dispatched_tasks:
            return "update"

        ftasks = dispatched_tasks[datainput[c.kafka_cluster]]
        if forwarder_stanza not in ftasks:
            return "update"

        topics = ftasks[forwarder_stanza][c.kafka_topic]
        for topic_info in topics:
            if topic_info[0] == datainput[c.kafka_topic]:
                if (topic_info[1] != datainput[c.kafka_partition] or
                        topic_info[-1] != datainput.get(c.index) or
                        topic_info[-2] != datainput.get(c.kafka_topic_group)):
                    return "update"
        return "update"

    def _create_or_update(self, clusters, dispatched_tasks, forwarder_stanza,
                          datainput, name, forwarder, conf_mgr):
        res = KafkaConfig._get_data_input_status(
            dispatched_tasks, forwarder_stanza, datainput, name, conf_mgr)
        if res == "create":
            logger.info("Create data input=%s on forwarder=%s",
                        name, forwarder[c.hostname])
            try:
                conf_mgr.create_data_input(c.kafka_mod, name, datainput)
            except req.ConfExistsException:
                pass
            except Exception:
                logger.error("Failed to create data input for=%s on "
                             "forwarder=%s, error=%s", name,
                             forwarder[c.hostname], traceback.format_exc())
                return False
        elif res == "update":
            logger.info("Update data input=%s on forwarder=%s",
                        name, forwarder[c.hostname])
            try:
                conf_mgr.update_data_input(c.kafka_mod, name, datainput)
            except Exception:
                logger.error("Failed to update data input for=%s on "
                             "forwarder=%s, error=%s", name,
                             forwarder[c.hostname], traceback.format_exc())
                return False

        # Commit to ckpt
        kafka_stanza = datainput[c.kafka_cluster]
        if kafka_stanza not in dispatched_tasks:
            dispatched_tasks[kafka_stanza] = {}

        topic_partition = [datainput[c.kafka_topic],
                           datainput[c.kafka_partition],
                           datainput[c.kafka_topic_group],
                           datainput[c.index]]

        forwarder_tasks = dispatched_tasks[kafka_stanza]
        if forwarder_stanza not in forwarder_tasks:
            forwarder_tasks[forwarder_stanza] = {
                c.kafka_brokers: clusters[kafka_stanza][c.kafka_brokers],
                c.kafka_topic: [topic_partition],
            }
        else:
            topic_partitions = forwarder_tasks[forwarder_stanza][c.kafka_topic]
            if res in ("update", "update_ckpt"):
                for topic_info in topic_partitions:
                    if topic_info[0] == datainput[c.kafka_topic]:
                        topic_info[-1] = datainput[c.index]
                        topic_info[-2] = datainput[c.kafka_topic_group]
                        topic_info[1] = datainput[c.kafka_partition]
                        break
                else:
                    logger.info("Topic=%s is not found in ckpt",
                                datainput[c.kafka_topic])
                    topic_partitions.append(topic_partition)
            else:
                assert topic_partition not in topic_partitions
                topic_partitions.append(topic_partition)

        self._store.update_state(c.dispatched_task_ckpt, dispatched_tasks)
        return True

    def _do_send_safe(self, clusters, dispatched_tasks, forwarder_stanza,
                      forwarder, settings, localhost):
        session_key = self._get_forwarder_session_key(forwarder)

        if not localhost and c.global_settings in settings["config_settings"]:
            logger.info("Config global settings for forwarder=%s",
                        forwarder[c.hostname])
            uri = ("{}/servicesNS/nobody/{}/kafka_input_setup"
                   "/kafka_settings/kafka_settings")
            url = uri.format(forwarder[c.hostname], self._appname)
            payload = {
                c.all_settings: json.dumps(settings["config_settings"])
            }
            resp, content = rest.splunkd_request(
                url, session_key, method="POST", data=payload)
            if resp is None or resp.status not in (200, 201):
                logger.error("Failed to update config settings on forwarder=%s",
                             forwarder[c.hostname])
                self._dispatch_errors = True
                return

        conf_mgr = cm.ConfManager(forwarder[c.hostname], session_key,
                                  app_name=self._appname)
        for name, datainput in settings["data_input_settings"].iteritems():
            res = self._create_or_update(
                clusters, dispatched_tasks, forwarder_stanza, datainput,
                name, forwarder, conf_mgr)
            if not res:
                self._dispatch_errors = True

    def _disable_tasks_on_forwarders(self, global_settings, kafka_clusters,
                                     forwarders, dispatched_tasks, topics):
        removed_clusters = set()
        failed_clusters = self._disable_tasks_for_deleted_clusters(
            kafka_clusters, forwarders, dispatched_tasks, removed_clusters)

        failed_clusters2 = self._disable_tasks_for_deleted_forwarders(
            global_settings, kafka_clusters, forwarders,
            dispatched_tasks, removed_clusters)
        failed_clusters.update(failed_clusters2)

        self._disable_tasks_for_deleted_topics(
            forwarders, dispatched_tasks, topics)
        return failed_clusters

    def _disable_tasks_for_deleted_clusters(self, kafka_clusters, forwarders,
                                            dispatched_tasks,
                                            removed_clusters):
        # 1) Delete tasks on remote forwarders by setting "removed = 1"
        # for removed kafka clusters
        logger.info("Delete tasks for deleted clusters")
        failed_clusters = set()
        for stanza_name, cluster in kafka_clusters.iteritems():
            if utils.is_false(cluster.get(c.removed)):
                continue

            if stanza_name not in dispatched_tasks:
                continue

            for forwarder_stanza in dispatched_tasks[stanza_name].keys():
                if forwarder_stanza not in forwarders:
                    logger.error("Forwarder=%s is in ckpt but not found in "
                                 "forwarder conf", forwarder_stanza)
                    del dispatched_tasks[stanza_name][forwarder_stanza]
                    continue

                forwarder = forwarders[forwarder_stanza]
                res = self._do_disable(forwarder, removed_clusters, stanza_name)
                if res:
                    del dispatched_tasks[stanza_name][forwarder_stanza]
                    logger.info("Remove cluster=%s forwarder=%s from ckpt",
                                stanza_name, forwarder_stanza)
                else:
                    failed_clusters.add(stanza_name)

            if not dispatched_tasks[stanza_name]:
                logger.info("Remove cluster=%s from ckpt", stanza_name)
                del dispatched_tasks[stanza_name]
        return failed_clusters

    def _disable_tasks_for_deleted_forwarders(
            self, global_settings, kafka_clusters, forwarders,
            dispatched_tasks, removed_clusters):
        # 2) Delete tasks on remote forwarders by setting "removed = 1"
        # for removed forwarders
        logger.info("Delete tasks for deleted forwarders")
        failed_clusters = set()
        for stanza_name, forwarder in forwarders.iteritems():
            if utils.is_false(forwarder.get(c.removed)):
                continue

            localhost = self.is_current_host(forwarder[c.hostname])
            if localhost:
                conf_mgr = cm.ConfManager(self._meta_configs[c.server_uri],
                                          self._meta_configs[c.session_key],
                                          app_name=self._appname)
                all_stanzas = conf_mgr.all_data_input_stanzas(c.kafka_mod)
                res = self._delete_data_inputs(kafka_clusters, global_settings,
                                               all_stanzas)

            for kafka_stanza in dispatched_tasks.keys():
                forwarder_tasks = dispatched_tasks[kafka_stanza]
                if stanza_name not in forwarder_tasks:
                    continue

                if kafka_stanza in removed_clusters:
                    logger.info("%s cluster has already been disabled",
                                kafka_stanza)
                    continue

                if not localhost:
                    res = self._do_disable(forwarder, removed_clusters,
                                           kafka_stanza)
                if res:
                    del forwarder_tasks[stanza_name]
                    logger.info("Remove forwarder=%s from kafka_cluster=%s in "
                                "ckpt", stanza_name, kafka_stanza)

                    if not dispatched_tasks[kafka_stanza]:
                        logger.info("Remove cluster=%s from ckpt",
                                    kafka_stanza)
                        del dispatched_tasks[kafka_stanza]
                else:
                    failed_clusters.add(kafka_stanza)
        return failed_clusters

    def _disable_tasks_for_deleted_topics(self, forwarders, dispatched_tasks,
                                          topics):
        if not dispatched_tasks:
            return

        logger.info("Delete tasks for deleted topics")
        # 1) Find all of the removed topics (due to topic white/blacklist
        # changed)
        removed_topics = self._get_deleted_topics(forwarders, dispatched_tasks,
                                                  topics)

        # 2) Remove the tasks for the corresponding removed topics
        try:
            self._do_disable_tasks_for_deleted_topics(
                forwarders, dispatched_tasks, topics, removed_topics)
        except Exception:
            logger.error("Failed to disable tasks for deleted topics=%s"
                         "error=%s", removed_topics, traceback.format_exc())

    def _get_deleted_topics(self, forwarders, dispatched_tasks, topics):
        removed_topics = {}
        for cluster_stanza, forwarder_topics in dispatched_tasks.iteritems():
            if cluster_stanza not in topics:
                logger.info("Unknown kafka cluster stanza=%s in ckpt",
                            cluster_stanza)
                continue

            cluster_topics = topics[cluster_stanza][c.kafka_topic]
            dispatched_topics = set()
            topic_to_forwarder = {}
            for forwarder_stanza, ftopics in forwarder_topics.iteritems():
                for topic in ftopics[c.kafka_topic]:
                    dispatched_topics.add(topic[0])
                    topic_to_forwarder[topic[0]] = forwarder_stanza

            if cluster_topics != dispatched_topics:
                removed = dispatched_topics - cluster_topics
                logger.info("Found removed topics=%s for cluster=%s",
                            removed, cluster_stanza)
                removed_topics[cluster_stanza] = (removed, topic_to_forwarder)
        return removed_topics

    def _do_disable_tasks_for_deleted_topics(self, forwarders,
                                             dispatched_tasks, topics,
                                             removed_topics):
        cached_conf_mgrs = {}
        for cluster_stanza, removed in removed_topics.iteritems():
            topics, topic_2_forwarder = removed
            for topic in topics:
                try:
                    self._do_remove_data_input(
                        topic, topic_2_forwarder, cluster_stanza, forwarders,
                        cached_conf_mgrs)
                except Exception:
                    logger.error("Failed to remove datainput for topic=%s "
                                 "cluster=%s on forwarder=%s, reason=%s",
                                 topic, cluster_stanza,
                                 topic_2_forwarder[topic],
                                 traceback.format_exc())
                    continue

                # Update ckpt
                t = dispatched_tasks[cluster_stanza][topic_2_forwarder[topic]]
                for i, topic_info in enumerate(t[c.kafka_topic]):
                    if topic == topic_info[0]:
                        del t[c.kafka_topic][i]
                        break
                self._store.update_state(c.dispatched_task_ckpt,
                                         dispatched_tasks)

    def _do_remove_data_input(self, topic, topic_2_forwarder, cluster_stanza,
                              forwarders, cached_conf_mgrs):
        forwarder_stanza = topic_2_forwarder[topic]
        forwarder = forwarders[forwarder_stanza]
        conf_mgr = self._get_cached_conf_mgr(
            forwarder_stanza, forwarder, cached_conf_mgrs)
        name = self._get_data_input_name(cluster_stanza, topic)
        try:
            conf_mgr.delete_data_input(c.kafka_mod, name)
        except req.ConfNotExistsException:
            pass

        logger.info("Deleted datainput=%s on forwarder=%s",
                    name, forwarder_stanza)

    def _get_cached_conf_mgr(self, forwarder_stanza, forwarder,
                             cached_conf_mgrs):
        if forwarder_stanza in cached_conf_mgrs:
            return cached_conf_mgrs[forwarder_stanza]

        session_key = self._get_forwarder_session_key(forwarder)
        conf_mgr = cm.ConfManager(forwarder[c.hostname], session_key,
                                  app_name=self._appname)
        cached_conf_mgrs[forwarder_stanza] = conf_mgr
        return conf_mgr

    def _do_disable(self, forwarder, removed_clusters, stanza_name):
        """
        :return: false if something goes wrong, true if everything is good
        """

        logger.info("Disable cluster=%s on forwarder=%s",
                    stanza_name, forwarder[c.hostname])
        try:
            session_key = self._get_forwarder_session_key(forwarder)
            conf_mgr = tcm.TAConfManager(
                c.myta_cred_conf, forwarder[c.hostname], session_key)
            conf_mgr.update({c.name: stanza_name, c.removed: "1"})
        except Exception:
            logger.error("Failed to disable cluster=%s, error=%s",
                         stanza_name, traceback.format_exc())
            return False
        else:
            removed_clusters.add(stanza_name)
            return True

    def _get_forwarder_session_key(self, forwarder):
        if not forwarder[c.hostname].startswith("https://"):
            forwarder[c.hostname] = "https://{}".format(forwarder[c.hostname])

        session_key = cred.CredentialManager.get_session_key(
            forwarder[c.username], forwarder[c.password],
            forwarder[c.hostname])
        return session_key

    def _remove_forwarders(self, forwarders, conf_mgr):
        for forwarder_stanza, forwarder in forwarders.iteritems():
            if utils.is_true(forwarder.get(c.removed)):
                if forwarder.get(c.appname):
                    conf_mgr.set_appname(forwarder.get(c.appname))
                else:
                    conf_mgr.set_appname(self._appname)
                try:
                    conf_mgr.delete(forwarder_stanza)
                except req.ConfNotExistsException:
                    pass
                except Exception:
                    logger.error("Failed to delete removed forwarder=%s,"
                                 "error=%s", forwarder_stanza,
                                 traceback.format_exc())

    def _remove_tasks(self, clusters, global_settings):
        conf_mgr = cm.ConfManager(self._meta_configs[c.server_uri],
                                  self._meta_configs[c.session_key],
                                  app_name=self._appname)
        all_stanzas = conf_mgr.all_data_input_stanzas(c.kafka_mod)
        stanzas_to_be_deleted = []
        for cluster_stanza, cluster in clusters.iteritems():
            if utils.is_false(cluster.get(c.removed)):
                continue

            logger.warn("Remove all tasks for cluster=%s", cluster_stanza)
            for stanza in all_stanzas:
                if stanza[c.kafka_cluster] != cluster_stanza:
                    continue

                stanzas_to_be_deleted.append(stanza)
        self._delete_data_inputs(clusters, global_settings,
                                 stanzas_to_be_deleted)

    def _delete_data_inputs(self, clusters, global_settings,
                            stanzas_to_be_deleted):
        """
        :return: false if something goes wrong, true if everything is good
        """

        has_exception = False
        global_settings = global_settings[c.global_settings]
        store = ss.get_state_store(
            self._meta_configs, self._appname,
            use_kv_store=global_settings.get(c.use_kv_store, False))

        conf_mgr = cm.ConfManager(self._meta_configs[c.server_uri],
                                  self._meta_configs[c.session_key],
                                  app_name=self._appname)
        kafka_clients = {}
        for stanza in stanzas_to_be_deleted:
            try:
                self._delete_ckpts(stanza, clusters, kafka_clients, store)
                conf_mgr.set_appname(stanza[c.appname])
                conf_mgr.delete_data_input(c.kafka_mod, stanza[c.name])
            except req.ConfNotExistsException:
                pass
            except Exception:
                has_exception = True
                logger.error("Failed to remove data input=%s, error=%s",
                             stanza[c.name], traceback.format_exc())
                continue

            if not has_exception:
                conf_mgr.set_appname(self._appname)
                conf_mgr.delete_stanza(
                    c.myta_cred_conf, stanza[c.kafka_cluster])
        return not has_exception

    @staticmethod
    def _delete_ckpts(stanza, clusters, kafka_clients, store):

        topic = stanza[c.kafka_topic]
        cluster = clusters[stanza[c.kafka_cluster]]
        partitions = KafkaConfig.get_partitions(stanza)
        if not partitions:
            client = KafkaConfig._get_client(cluster, kafka_clients)
            if topic not in client.topic_partitions:
                logger.warn("Topic=%s is not found in cluster=%s",
                            topic, stanza[c.kafka_cluster])
                return
            partitions = client.topic_partitions[topic]

        brokers = b64encode(cluster[c.kafka_brokers])
        for pid in partitions:
            key = "{}_{}_{}".format(brokers, topic, pid)
            logger.info("Delete ckpt=%s", key)
            store.delete_state(key)

    @staticmethod
    def _get_client(cluster, kafka_clients):
        try:
            brokers = cluster[c.kafka_brokers]
            if brokers not in kafka_clients:
                kafka_clients[brokers] = kq.get_kafka_client(cluster)
            return kafka_clients[brokers]
        except Exception:
            msg = "Failed to connect to Kafka brokers={}, error={}".format(
                cluster[c.kafka_brokers], traceback.format_exc())
            logger.error(msg)
            raise Exception(msg)

    @staticmethod
    def _get_topics(kafka_clusters):
        """
        Query and filter topic according to topic blacklist and whitelist
        :return: {
            cluster_stanza_name: {
                kafka_topic: set([topic1, topic2, ...]),
                kafka_partition: partitions,
                kafka_topic_group: topic_group,
                index: index,
            }
        }
        """

        topic_set = {}
        all_topics = {}
        kafka_clients = {}
        for cluster_stanza, cluster in kafka_clusters.iteritems():
            if utils.is_true(cluster.get(c.removed)):
                continue

            client = KafkaConfig._get_client(cluster, kafka_clients)
            topics = set(client.topic_partitions.keys())
            if not topics:
                # We treat this case an error since sometimes kafka python
                # bining quirks and which can result in data inputs deletion

                msg = "Didn't get any topic from Kafka brokers={}".format(
                    cluster[c.kafka_brokers])
                logger.error(msg)
                raise Exception(msg)

            try:
                topics = KafkaConfig._filter_topics(topics, cluster)
            except Exception:
                logger.error("Failed to filter topics, error=%s",
                             traceback.format_exc())
                continue

            partitions = KafkaConfig.get_partitions(cluster)
            partitions = ",".join(str(pid) for pid in partitions)

            # For now, just reporting
            KafkaConfig._handle_dup_topic_partition(
                cluster, topics, partitions, topic_set)
            all_topics[cluster_stanza] = {
                c.kafka_topic: topics,
                c.kafka_partition: partitions,
                c.kafka_topic_group: cluster.get(c.kafka_topic_group),
                c.index: cluster.get(c.index),
            }
        return all_topics

    @staticmethod
    def _handle_dup_topic_partition(cluster, topics, partitions, topic_set):
        deduped_topics = set()
        if partitions:
            hpartitions = set(partitions.split(","))
        else:
            hpartitions = set()

        if cluster[c.kafka_brokers] not in topic_set:
            topic_set[cluster[c.kafka_brokers]] = {}

        kafka_topics = topic_set[cluster[c.kafka_brokers]]
        for topic in topics:
            if topic not in kafka_topics:
                kafka_topics[topic] = hpartitions
                deduped_topics.add(topic)
            else:
                if (not kafka_topics[topic] or not hpartitions or
                        kafka_topics[topic].intersection(hpartitions)):
                    kafka_topics[topic] = kafka_topics[topic].union(hpartitions)
                    logger.warn("Found dup brokers=%s, topic=%s, partition=%s",
                                cluster[c.kafka_brokers], topic, partitions)

        return deduped_topics

    @staticmethod
    def _filter_partitions(stanza, topics, cluster, kafka_clients):
        partition_ids = KafkaConfig.get_partitions(stanza)
        if not partition_ids:
            return []

        client = KafkaConfig._get_client(cluster, kafka_clients)
        valid_ids = set(partition_ids)
        for topic in topics:
            for pid in partition_ids:
                if pid not in client.topic_partitions[topic]:
                    if pid in valid_ids:
                        valid_ids.remove(pid)
                    logger.error("Invalid partition_id=%s for topic=%s",
                                 pid, topic)
        return valid_ids

    @staticmethod
    def _filter_topics(topics, cluster):
        filtered = set()
        whitelist = cluster.get(c.topic_whitelist)
        if whitelist:
            whitelist = "^{}$".format(whitelist)

        blacklist = cluster.get(c.topic_blacklist)
        if blacklist:
            blacklist = "^{}$".format(blacklist)

        for topic in topics:
            if whitelist:
                m = re.search(whitelist, topic)
                if m:
                    logger.info("topic=%s matches whitelist=%s",
                                topic, whitelist)
                    filtered.add(topic)
                continue

            if blacklist:
                m = re.search(blacklist, topic)
                if m:
                    logger.info("topic=%s matches blacklist=%s",
                                topic, blacklist)
                else:
                    filtered.add(topic)
                continue

            filtered.add(topic)
        return filtered

    def _global_settings_changed(self, global_settings):
        g_settings = self._store.get_state(c.global_settings_ckpt)
        changed = False
        if not g_settings:
            changed = True
        else:
            for k, v in global_settings.iteritems():
                if g_settings.get(k) != v:
                    self._store.update_state(c.global_settings_ckpt,
                                             global_settings)
                    changed = True
                    break
        if changed:
            self._store.update_state(c.global_settings_ckpt, global_settings)
            logger.info("Detect global settings changed")
        return changed

    def is_current_host(self, hostname):
        hostname, port = extract_hostname_port(hostname)
        if port != self._port:
            return False

        local_hosts = ["localhost", "127.0.0.1", self._servername]
        if hostname in local_hosts:
            return True

        hostname = hostname.lower()
        if hostname == self._current_hostname:
            return True

        if not self._current_addrs:
            return False

        if (hostname == self._current_addrs[0] or
                hostname in self._current_addrs[-1]):
            return True

        return False
