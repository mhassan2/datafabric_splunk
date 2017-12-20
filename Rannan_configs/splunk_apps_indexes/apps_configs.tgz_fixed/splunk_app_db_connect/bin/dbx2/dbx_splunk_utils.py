import splunk.util as util
from splunk import ResourceNotFound
import splunk.entity as en
from dbx_logger import logger

"""
Seems now splunk getEntity will get disabled entity as well, this method provides the alternative that only get non-disabled entity
It is able to identify the joined entities too, any joined entities are disabled, the entity is disabled. 
"""
def getEntity(entityPath, name, namespace=None, owner=None, sessionKey=None, hostPath=None, available=True):
    conn = en.getEntity(entityPath, name, 
                        namespace=namespace,
                        owner=owner,
                        sessionKey=sessionKey,
                        hostPath=hostPath)

    params = conn.properties
    
    if available:
        for n, v in params.items():
            if n in ["disabled"] and util.normalizeBoolean(v):
                raise ResourceNotFound(msg="%s Resource is disabled." % name)
            elif n.endswith(".disabled"):
                if v in ["-1"]:
                    raise ResourceNotFound(msg="%s in %s Resource not found." % (n[:len(n)-9], name))
                elif util.normalizeBoolean(v):
                    raise ResourceNotFound(msg="%s in %s Resource is disabled." % (n[:len(n)-9], name))
    
    return conn


"""
Seems now splunk getEntities will get "disabled" entities as well, this method provides the alternative that only get non-disabled entities
Identifying disabled entity is based on if any of joined entities is disabled, this entity is disabled. 
"""
def getEntities(entityPath, namespace=None, owner=None, sessionKey=None, count=None, offset=0, hostPath=None, available=True):
    conns = en.getEntities(entityPath,
                           namespace=namespace,
                           owner=owner,
                           count=count,
                           offset=offset,
                           sessionKey=sessionKey,
                           hostPath=hostPath)

    for name in conns:
        params = conns[name].properties
        if available:
            for n, v in params.items():
                if n in ["disabled"] or n.endswith(".disabled"):
                    if v in ["-1"] or util.normalizeBoolean(v):
                        del conns[name]

    return conns
    
