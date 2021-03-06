from unittest import TestCase
from flask.testing import FlaskClient
import os
import json
from datetime import datetime,timezone

from ddb_single_table_obj import DDB_Single_Table
ddb = DDB_Single_Table()
print("initialize DDB object {}".format(ddb))

settings_id = "Y2lzY29zcGFyazovL3VzL1BFT1BMRS82MzFlODQ0Mi02YTU3LTQ1ZTAtYjIyNy1jYWQ1Y2FkMmQ5MWQ"
TEST_SETTINGS_1 = {"language": "cs_CZ", "partial_results": True, "active_votes": False, "user_1_1": False, "user_updated": False, 'timestamp': '1970-01-01T01:00Z'}
TEST_SETTINGS_2 = {"language": "en_US", "partial_results": True, "active_votes": False, "user_1_1": False, "user_updated": False, 'timestamp': '1970-01-01T01:00Z'}

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
        self.assertEqual(stngs.settings, TEST_SETTINGS_2)
        
    def test_set_settings(self):
        stngs = BotSettings()
        stngs.settings = {"language": "cs_CZ"}
        self.assertEqual(stngs.settings, TEST_SETTINGS_1)
    
    def test_db_save_user_settings(self):
        stngs = BotSettings(db = ddb, settings_id = settings_id)
        stngs.settings = {"language": "cs_CZ"}
        stngs.save()
        stngs2 = BotSettings(db = ddb, settings_id = settings_id)
        stngs2.load()
        self.assertEqual(stngs.settings, stngs2.settings)
        self.assertEqual(stngs.stored, True)
        
    def test_non_existent_settings(self):
        stngs = BotSettings(settings_id = "NON_EXISTENT")
        stngs.load()
        self.assertEqual(stngs.stored, False)
        
    def test_timestamp(self):
        stngs = BotSettings()
        self.assertEqual(stngs.timestamp, datetime.fromtimestamp(0).replace(tzinfo=timezone.utc))
        stngs.save()
        self.assertEqual(stngs.timestamp, datetime.fromtimestamp(stngs.timestamp.timestamp(), timezone.utc))
        
if __name__ == "__main__":
    unittest.main()
