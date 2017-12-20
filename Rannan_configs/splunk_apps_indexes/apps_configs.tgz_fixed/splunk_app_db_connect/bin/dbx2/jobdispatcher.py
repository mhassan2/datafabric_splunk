import random

from splunk import ResourceNotFound
import splunk.admin as admin
import splunk.entity as en
import core.remote_auth as auth
from dbx_logger import logger

DBPOOL_ENDPOINT = 'db_connect/dbpool'
RESOURCEPOOL_ENDPOINT = 'db_connect/resourcepool'
POOLHEALTH_ENDPOINT = 'db_connect/poolhealth'

class JobDispatcher(object):
    def chooseTarget(self, servers):
        target = random.choice(servers)
        return target
    def getTarget(self, resource_pool, namespace=None, owner=None, sessionKey=None, hostPath=None):
        ent = en.getEntity(RESOURCEPOOL_ENDPOINT, resource_pool, namespace=namespace, owner=owner, sessionKey=sessionKey, hostPath=hostPath)
        healthyServers = []
        for node in ent['nodes'].split(';'):
            health = None
            logger.debug("Processing node %s" % node)
            try:
                health = en.getEntity(POOLHEALTH_ENDPOINT, node, namespace=namespace, owner=owner, sessionKey=sessionKey, hostPath=hostPath)
            except ResourceNotFound:
                logger.error("Health entity %s not found" % node)
                pass
            except Exception as e:
                logger.error("Health entity error %s" % e)
            if health is not None and health['alive'] == '1':
                logger.debug("Getting server info for %s %s %s" % (ent.id, node, sessionKey))
                remoteKey = auth.getRemoteKey(node, sessionKey)
                serverStatus = self.getRpcServerInfo(node, namespace=None, owner=None, sessionKey=remoteKey)
                if serverStatus is not None:
                    healthyServers.append(serverStatus)
        
        if not healthyServers:
            logger.error("no healthy targets")
            return None
        target = self.chooseTarget(healthyServers)
        logger.info("target node = %s:%s\n" % (target["host"], target["port"]))
        return target
                           
    def getRpcServerInfo(self, url, namespace=None, owner=None, sessionKey=None):
        node_status = None
        try:
            node_status = en.getEntity("", "", uri=url, namespace=namespace, owner=owner, sessionKey=sessionKey)
        except Exception as e:
            logger.error("getRpcServerInfo error %s" % e)
            pass
        return node_status
    
