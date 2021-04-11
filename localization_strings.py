from unidecode import unidecode

LANGUAGES = {
    "cs_CZ": "Čeština",
    "en_US": "English, United States"
}

def lang_list_for_card():
    lan_list = []
    for (key, value) in LANGUAGES.items():
        lan_list.append({"title": value, "value": key})
        
    lan_list.sort(key=lambda x: unidecode(x["title"]).lower())
    
    return lan_list

CS_CZ = {
    "loc_default_form_msg": "Toto je formulář. Zobrazíte si ho v aplikaci nebo webovém klientovi Webex.",
    "loc_bot_welcome_1": "Vítá vás bot pro řízení hlasování",
    "loc_bot_welcome_2": "Zahajte prosím novou schůzi",
    "loc_bot_welcome_3": "Zahájit novou schůzi",
    "loc_bot_welcome_4": "Název schůze",
    "loc_bot_welcome_5": "Napište název",
    "loc_bot_welcome_6": "Zahájit",
    "loc_poll_block_1": "Hlasování",
    "loc_poll_block_2": "Téma",
    "loc_poll_block_3": "Napište téma",
    "loc_poll_block_4": "Časový limit",
    "loc_poll_block_5": "minuta",
    "loc_poll_block_6": "minuty",
    "loc_poll_block_7": "Zahájit hlasování",
    "loc_next_poll_block_1": "Další hlasování",
    "loc_end_meeting_block_1": "Ukončit schůzi",
    "loc_end_meeting_block_2": "Ukončit",
    "loc_start_meeting_1": "Schůze",
    "loc_start_meeting_2": "zahájena",
    "loc_start_meeting_3": "zahájil schůzi",
    "loc_start_meeting_4": "Klikněte na tlačítko",
    "loc_start_meeting_5": "Přítomen",
    "loc_start_meeting_6": "Jinak bude vaše přítomnost zaznamenána až od chvíle, kdy se aktivně zúčastníte hlasování",
    "loc_start_meeting_7": "Přítomen",
    "loc_start_meeting_8": "Hlasování",
    "loc_start_meeting_9": "Ukončit hlasování",
    "loc_start_meeting_10": "Ukončit",
    "loc_end_meeting_1": "Schůze ukončena",
    "loc_end_meeting_2": "ukončil schůzi",
    "loc_end_meeting_3": "Zahájit novou schůzi",
    "loc_end_meeting_4": "Název schůze",
    "loc_end_meeting_5": "Napište název",
    "loc_end_meeting_6": "Zahájit",
    "loc_submit_poll_1": "Téma",
    "loc_submit_poll_2": "Napište téma",
    "loc_submit_poll_3": "Časový limit",
    "loc_submit_poll_4": "minuta",
    "loc_submit_poll_5": "minuty",
    "loc_submit_poll_6": "Zahájit hlasování",
    "loc_submit_poll_7": "Ukončit schůzi",
    "loc_submit_poll_8": "Ukončit",
    "loc_poll_template_1": "zahájil hlasování",
    "loc_poll_template_2": "Téma hlasování",
    "loc_poll_template_3": "Časový limit",
    "loc_poll_template_4": "Pro",
    "loc_poll_template_5": "Proti",
    "loc_poll_template_6": "Zdržuji se",
    "loc_poll_results_1": "výsledky hlasování",
    "loc_poll_results_2": "Pro",
    "loc_poll_results_3": "Proti",
    "loc_poll_results_4": "Zdržel se",
    "loc_settings_block_1": "Language",
    "loc_settings_block_2": "Select language",
    "loc_settings_block_3": "Publish partial results after each vote",
    "loc_settings_block_4": "Yes",
    "loc_settings_block_5": "No",
    "loc_user_settings_1": "Bot Settings",
    "loc_user_settings_2": "Settings will be applied to any new meeting created by you in any Space. If you want to change the meeting settings later, visit this form and change the settings before the meeting start.",
    "loc_user_settings_3": "Save",
    "loc_room_settings_1": "Bot Settings",
    "loc_room_settings_2": "Settings will be applied to any new meeting created in this Space. If you want to change the meeting settings later, visit this form and change the settings before the next meeting start.",
    "loc_room_settings_3": "Save"
}

EN_US = {

}

LOCALES = {
    "cs_CZ": CS_CZ,
    "en_US": EN_US
}
