from unittest import TestCase
from flask.testing import FlaskClient
import config_test
import os
import json

import wxt_compliance as wxt

class BotTest(TestCase):
    
    def setUp(self):
        print("\nsetup {}".format(self.__class__.__name__))
        wxt.flask_app.testing = True
        self.client = wxt.flask_app.test_client()
                
    def tearDown(self):
        print("tear down {}".format(self.__class__.__name__))


if __name__ == "__main__":
    unittest.main()
