from unittest import TestCase
from flask.testing import FlaskClient
import os
import json

from ddb_single_table_obj import DDB_Single_Table
ddb = DDB_Single_Table()
print("initialize DDB object {}".format(ddb))

USER_ID = "Y2lzY29zcGFyazovL3VzL1BFT1BMRS82MzFlODQ0Mi02YTU3LTQ1ZTAtYjIyNy1jYWQ1Y2FkMmQ5MWQ"
TEST_SETTINGS_1 = {"language": "Czech", "partial_results": False, "active_votes": True}

from settings import BotSettings

class BotTest(TestCase):
    
    def setUp(self):
        print("\nsetup {}".format(self.__class__.__name__))
        # wxt.flask_app.testing = True
        # self.client = wxt.flask_app.test_client()
                
    def tearDown(self):
        print("tear down {}".format(self.__class__.__name__))
        
    def test_default_settings(self):
        stngs = BotSettings()
        self.assertEqual(stngs.settings, {"language": "English", "partial_results": True, "active_votes": False})
        
    def test_set_settings(self):
        stngs = BotSettings()
        stngs.settings = {"language": "Czech"}
        self.assertEqual(stngs.settings, {"language": "Czech", "partial_results": True, "active_votes": False})
    
    def test_db_save_user_settings(self):
        stngs = BotSettings(db = ddb, user_id = USER_ID)
        stngs.settings = {"language": "Czech"}
        stngs.save()
        stngs2 = BotSettings(db = ddb, user_id = USER_ID)
        stngs2.load()
        self.assertEqual(stngs.settings, stngs2.settings)
        
if __name__ == "__main__":
    unittest.main()
