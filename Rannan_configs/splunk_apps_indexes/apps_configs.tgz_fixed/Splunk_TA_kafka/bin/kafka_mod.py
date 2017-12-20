#!/usr/bin/python

"""
This is the main entry point for My TA
"""

import sys
import traceback
import time
import os
import os.path as op

import splunktalib.common.util as utils
import splunktalib.modinput as modinput
import splunktalib.file_monitor as fm
import splunktalib.orphan_process_monitor as opm
from splunktalib.common import log
import kafka_config as kc
import kafka_consts as c
import kafka_concurrent_data_loader as kcdl


utils.remove_http_proxy_env_vars()
utils.disable_stdout_buffer()

logger = log.Logs().get_logger("main")


def do_scheme():
    """
    Feed splunkd the TA's scheme
    """

    desc = ("Enable modular inputs to collect Kafka topic data. Use only if "
            "managing inputs manually from individual forwarders. "
            "See documentation for details.")
    print """
    <scheme>
    <title>Splunk Add-on for {}</title>
    <description>{}</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>{}</use_single_instance>
    <endpoint>
      <args>
        <arg name="name">
          <title>Kafka Data Input Name</title>
        </arg>
        <arg name="kafka_cluster" required_on_create="true">
          <title>Kafka cluster</title>
        </arg>
        <arg name="kafka_topic" required_on_create="true">
           <title>Kafka topic name</title>
        </arg>
        <arg name="kafka_partition" required_on_create="false">
           <title>Kafka partitions</title>
        </arg>
        <arg name="kafka_partition_offset" required_on_create="true">
           <title>Kafka partition offset</title>
        </arg>
        <arg name="kafka_topic_group" required_on_create="false">
           <title>Kafka topic group</title>
        </arg>
      </args>
    </endpoint>
    </scheme>
    """.format(c.ta_short_name, desc, kcdl.use_single_instance())


def _handle_file_changes(data_loader):
    """
    :reload conf files and exit
    """

    def _handle_refresh(changed_files):
        logger.info("Detect %s changed, reboot itself", changed_files)
        data_loader.stop()

    return _handle_refresh


def _handle_topic_changes(data_loader, kconfig):

    def _do_handle_topic_changes():
        if kconfig.topics_changed():
            logger.info("Detect topics changed, reload...")
            data_loader.stop()
    return _do_handle_topic_changes


def _get_conf_files():
    cur_dir = op.dirname(op.dirname(op.abspath(__file__)))
    files = []
    for f in (c.myta_conf, c.myta_cred_conf, c.myta_forwarder_conf):
        files.append(op.join(cur_dir, "local", f + ".conf"))
    return files


def run():
    """
    Main loop. Run this TA forever
    """

    # Sleep 5 seconds here for KV store ready
    time.sleep(5)
    kc.setup_signal_handler(None, None)
    kconfig = kc.create_kafka_config()
    task_configs = kconfig.get_task_configs()
    if not task_configs and not kconfig.is_dispatcher():
        return

    loader = kcdl.KafkaDataLoaderManager(task_configs)
    kc.setup_signal_handler(loader, kconfig)

    monitor = fm.FileMonitor(_handle_file_changes(loader), _get_conf_files())
    loader.add_timer(monitor.check_changes, time.time(), 10)

    orphan_checker = opm.OrphanProcessChecker(loader.stop)
    loader.add_timer(orphan_checker.check_orphan, time.time(), 1)

    for i in range(15):
        if loader.received_stop_signal():
            return
        time.sleep(1)

    topic_interval = int(os.environ.get("kafka_topic_check_internval", 3600))
    if kconfig.is_dispatcher():
        topic_handler = _handle_topic_changes(loader, kconfig)
        loader.add_timer(topic_handler, time.time(), topic_interval)
    loader.start()


def validate_config():
    """
    Validate inputs.conf
    """

    _, configs = modinput.get_modinput_configs_from_stdin()
    return 0


def usage():
    """
    Print usage of this binary
    """

    hlp = "%s --scheme|--validate-arguments|-h"
    print >> sys.stderr, hlp % sys.argv[0]
    sys.exit(1)


def main():
    """
    Main entry point
    """

    args = sys.argv
    if len(args) > 1:
        if args[1] == "--scheme":
            do_scheme()
        elif args[1] == "--validate-arguments":
            sys.exit(validate_config())
        elif args[1] in ("-h", "--h", "--help"):
            usage()
        else:
            usage()
    else:
        logger.info("Start %s", c.ta_name)
        try:
            run()
        except Exception:
            logger.error("Encounter exception=%s", traceback.format_exc())
        logger.info("End %s", c.ta_name)
    sys.exit(0)


if __name__ == "__main__":
    main()
