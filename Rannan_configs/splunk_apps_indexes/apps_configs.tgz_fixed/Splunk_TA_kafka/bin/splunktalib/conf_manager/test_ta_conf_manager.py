import sys
import unittest as ut

sys.path.append("../")

# import base_case as bc
import splunktalib.conf_manager.ta_conf_manager as tcm
import splunktalib.credentials as cred


import xml.etree.ElementTree as ET
import urllib
import urllib2


def login(host="https://localhost:8089/", username='admin',
          password='changeme', ):
    data = {'username': username, 'password': password}
    data = urllib.urlencode(data)
    f = urllib2.urlopen(host + "/services/auth/login", data)
    session_key = ET.parse(f).find('sessionKey').text
    return session_key


class TestConfManager(ut.TestCase):

    def setUp(self):
        self.session_key = cred.CredentialManager.get_session_key(
            "admin", "admin")
        self.splunkd_uri = "https://localhost:8089"

    def testAll(self):
        mgr = tcm.TAConfManager("not_exist.conf", self.splunkd_uri,
                                self.session_key, "search")

        data = {
            "name": "localforwarder1",
            "username": "admin",
            "password": "admin",
        }

        data2 = {
            "name": "localforwarder2",
            "username": "admin",
            "password": "admin",
        }

        mgr.delete(data["name"])
        mgr.delete(data2["name"])
        mgr.set_encrypt_keys(["username", "password"])
        res = mgr.create(data)
        self.assertIsNone(res)
        res = mgr.get(data["name"])
        for key, val in data.iteritems():
            self.assertEqual(val, res[key])

        data["username"] = "admin2"
        mgr.update(data)
        res = mgr.get(data["name"])
        for key, val in data.iteritems():
            self.assertEqual(val, res[key])

        res = mgr.create(data2)
        self.assertIsNone(res)
        results = mgr.all(return_acl=False)
        for key, stanza in results.iteritems():
            if key == data["name"]:
                for key, val in data.iteritems():
                    self.assertEqual(val, stanza[key])
            elif key == data2["name"]:
                for key, val in data2.iteritems():
                    self.assertEqual(val, stanza[key])
            else:
                self.assertTrue(False)

        res = mgr.delete(data["name"])
        self.assertIsNone(res)
        res = mgr.delete(data2["name"])
        self.assertIsNone(res)

        res = mgr.update(data)
        self.assertIsNone(res)
        res = mgr.get(data["name"])
        for key, val in data.iteritems():
            self.assertEqual(val, res[key])
        res = mgr.delete(data["name"])
        self.assertIsNone(res)


if __name__ == "__main__":
    ut.main()
