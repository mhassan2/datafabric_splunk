import traceback


import splunk.clilib.cli_common as scc
import splunk.admin as admin


from splunktalib.common import log
import splunktalib.common.util as utils
from splunktalib.conf_manager import conf_manager as conf
import kafka_consts as c
import kafka_wrapper.kafka_queue as kq


logger = log.Logs().get_logger("custom_rest")


class KafkaRestHandler(admin.MConfigHandler):
    kafka_cluster_filter = "kafka_cluster_filter"
    kafka_topic_filter = "kafka_topic_filter"

    valid_params = ["kafka_cluster_filter", "kafka_topic_filter",
                    "kafka_cluster"]

    def setup(self):
        for param in self.valid_params:
            self.supportedArgs.addOptArg(param)

    def handleList(self, conf_info):
        logger.info("start list")
        self._doList(self.callerArgs, conf_info)
        logger.info("end list")

    def _doList(self, caller_args, conf_info):
        endpoints = {
            self.kafka_cluster_filter: self._handleKafkaClusterList,
            self.kafka_topic_filter: self._handleKafkaTopicList,
        }

        msgs = {
            self.kafka_cluster_filter: ("Failed to populate Kafka Cluster "
                                        "configuration. Please verify the "
                                        "Kafka Cluster configuration in "
                                        "setup UI."),
            self.kafka_topic_filter: ("Failed to populate Kafka Cluster "
                                      "topics. Please verify the Kafka Cluster"
                                      " is up and running and the Kafka "
                                      "Cluster configuration in setup UI is "
                                      "valid.")
        }

        for k in endpoints.iterkeys():
            if k in caller_args.iterkeys():
                try:
                    return endpoints[k](caller_args, conf_info)
                except Exception:
                    logger.error("Failed to do rest, error=%s",
                                 traceback.format_exc())
                    raise Exception(msgs[k])

        msg = "Unknown request {}".format(caller_args)
        logger.error(msg)
        raise Exception(msg)

    def _handleKafkaClusterList(self, caller_args, conf_info):
        conf_mgr = conf.ConfManager(scc.getMgmtUri(), self.getSessionKey())
        conf_mgr.reload_conf(c.myta_cred_conf)
        all_creds = conf_mgr.all_stanzas_as_dicts(c.myta_cred_conf)
        all_creds = {k: v for k, v in all_creds.iteritems()
                     if utils.is_false(v.get(c.removed))}

        # _ = caller_args[self.kafka_cluster_filter],
        conf_info["kafka_clusters"].append("clusters", all_creds.keys())

    def _handleKafkaTopicList(self, caller_args, conf_info):
        conf_mgr = conf.ConfManager(scc.getMgmtUri(), self.getSessionKey())
        conf_mgr.reload_conf(c.myta_cred_conf)
        all_creds = conf_mgr.all_stanzas_as_dicts(c.myta_cred_conf)
        kafka_cluster = all_creds.get(caller_args["kafka_cluster"][0])
        if kafka_cluster:
            client = kq.get_kafka_client(kafka_cluster)
            topics = set(client.topic_partitions.keys())
            topics = [topic for topic in topics]
            conf_info["kafka_topics"].append("topics", topics)
        else:
            msg = "Unknown Kafka cluster {}".format(
                caller_args["kafka_cluster"])
            logger.error(msg)
            raise Exception(msg)


def main():
    admin.init(KafkaRestHandler, admin.CONTEXT_NONE)


if __name__ == "__main__":
    main()
