from dbx_logger import logger

import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import avro.ipc as ipc
import avro.protocol as avro
import time, random
from avro.protocol import md5

avro_protocol_path = os.path.join(os.path.dirname(__file__), 'avro_protocol.json')
with open(avro_protocol_path, 'r') as avro_protocol_file:
    PROTOCOL = avro_protocol_file.read()

RPC_MESSAGES = json.loads(PROTOCOL)['messages']

"""
DBX-857 - avro detects the instance of client protocol and builds a hashset of protocols with md2 of instance v.s. protocol
so in handskaking, the server can recognize the client instance (for example if we have multiple versions of clients etc.
Unfortunately in splunk, we keep creating client instance for each request, therefore, we will repeatedly create protocol
instances, even though they are all the same. The fix is to make our protocol with unique id as below, so any instance of
sevice protocol will come with the same md5 of id. The backend now will just keep one entry only.
"""
SERVICE = avro.parse(PROTOCOL)
SERVICE._md5 = md5("splunk_app-db_connect").digest()

class Channel(object):

    def send(self, name, params):
        pass

    def close(self):
        pass

class AvroChannel(Channel):

    def __init__(self, protocol=SERVICE, host="localhost", port=9998, useSSL=False, req_resource="/dbx2/"):
        super(AvroChannel, self).__init__()

        self.protocol = protocol
        assert self.protocol != None

        self.host = host
        self.port = port
        self.useSSL = useSSL
        self.req_resource = req_resource


    def send(self, name, params):
        if self.useSSL:
            client = ipc.HTTPSTransceiver(self.host, self.port, req_resource=self.req_resource)
        else:
            client = ipc.HTTPTransceiver(self.host, self.port, req_resource=self.req_resource)
        self.requestor = ipc.Requestor(self.protocol, client)

        return self.requestor.request(name, params)


class px(object):
    def __init__(self, channel, name, reqs):
        self.name = name
        self.reqs = reqs
        self.channel = channel

    def __call__(self, *arguments):
        req_datum = dict()
        n = 0
        for r in self.reqs:
            req_datum[r["name"]] = arguments[n] if n < len(arguments) else None
            n = n + 1

        return self.channel.send(self.name, req_datum)


def build_service(channel, cls=object, protocol=PROTOCOL, max_retries=5, verified=True):
    error = None
    max_retries = max_retries + 1
    ms = dict()
    for msg, v in RPC_MESSAGES.items():
        ms[msg] = px(channel, msg, v["request"])

    srv = type(cls.__name__, (cls, ), ms)

    if verified is False:
        return srv

    for i in range(1, max_retries):
        try:
            srv.getServerStatus(["SPLUNK_HOME"])
            return srv
        except BaseException as ex:
            logger.debug('action=rpc_server_is_not_ready_to_serve_yet error="%s"', ex.message)
            time.sleep(5 * random.random() * i)
            error = ex

    if error is not None:
        raise error
