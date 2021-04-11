from unittest import TestCase
from flask.testing import FlaskClient
import os
import json

import bot_buttons_cards as bc
import localization_strings as ls

TEST_SETTINGS_1 = {"language": "Czech", "partial_results": True, "active_votes": False, "user_1_1": False}
TEST_SETTINGS_2 = {"language": "English", "partial_results": True, "active_votes": False, "user_1_1": False}

TEST_DICT_1 = {"a": "test {{test_1}}", "b": [{"c": "{{test_1}}"}, "{{test_1}}"]}
TEST_RES_1 = {"a": "test aaa", "b": [{"c": "aaa"}, "aaa"]}
TEST_DICT_2 = {"a": "test {{loc_poll_block_5}}", "b": [{"c": "{{loc_poll_block_6}}"}, "{{loc_poll_results_3}}"]}
TEST_REPLACE_2 = {"loc_poll_block_5": "minuta", "loc_poll_block_6": "minuty", "loc_poll_results_3": "Proti"}
TEST_RES_2 = {"a": "test minuta", "b": [{"c": "minuty"}, "Proti"]}
TEST_REPLACE_LANG = {
    "en_US": {"test_1": "minute", "test_2": "minutes", "test_3": "Nay"},
    "cs_CZ": {"test_1": "minuta", "test_2": "minuty", "test_3": "Proti"}
}
TEST_RES_3_EN = {"a": "test minute", "b": [{"c": "minutes"}, "Nay"]}
TEST_RES_3_CZ = {"a": "test minuta", "b": [{"c": "minuty"}, "Proti"]}

CARD_LIST_TEST_1 = [
    {
        "title": "Čeština",
        "value": "cs_CZ"
    },
    {
        "title": "English, United States",
        "value": "en_US"
    }
]

TEST_STRING_1 = "{{loc_poll_block_5}} {} {{loc_poll_block_6}}"
TEST_RES_4 = "minuta {} minuty"

from settings import BotSettings

class ButtonsCardsTest(TestCase):
    
    def setUp(self):
        print("\nsetup {}".format(self.__class__.__name__))
        # wxt.flask_app.testing = True
        # self.client = wxt.flask_app.test_client()
                
    def tearDown(self):
        print("tear down {}".format(self.__class__.__name__))
        
    def test_nested(self):
        stngs = BotSettings()
        res_1 = bc.nested_replace(TEST_DICT_1.copy(), "test_1", "aaa")
        self.assertEqual(res_1, TEST_RES_1)
        
    def test_nested_dict(self):
        stngs = BotSettings()
        res_2 = bc.nested_replace_dict(TEST_DICT_2.copy(), TEST_REPLACE_2)
        self.assertEqual(res_2, TEST_RES_2)
                    
    def test_nested_localize(self):
        stngs = BotSettings()
        res_3 = bc.localize(TEST_DICT_2.copy(), "en_US")
        self.assertEqual(res_3, TEST_RES_3_EN)
        res_3 = bc.localize(TEST_DICT_2.copy(), "cs_CZ")
        self.assertEqual(res_3, TEST_RES_3_CZ)
        
    def test_lang_list(self):
        card_list = ls.lang_list_for_card()
        self.assertEqual(card_list, CARD_LIST_TEST_1)
        
    def test_string(self):
        stngs = BotSettings()
        res_4 = bc.nested_replace_dict(TEST_STRING_1, TEST_REPLACE_2)
        self.assertEqual(res_4, TEST_RES_4)
                        
if __name__ == "__main__":
    unittest.main()
