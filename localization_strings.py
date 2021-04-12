from unidecode import unidecode

# language list which is presented in settings
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

# each language has to have it's own constant here
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
    "loc_poll_block_8": "Vyberte limit",
    "loc_next_poll_block_1": "Další hlasování",
    "loc_end_meeting_block_1": "Ukončit schůzi",
    "loc_end_meeting_block_2": "Ukončit",
    "loc_start_meeting_1": "Schůze",
    "loc_start_meeting_2": "zahájena",
    "loc_start_meeting_3": "zahájil schůzi",
    "loc_start_meeting_4": "Klikněte na tlačítko",
    "loc_start_meeting_5": "Přítomen",
    "loc_start_meeting_6": ". Jinak bude vaše přítomnost zaznamenána až od chvíle, kdy se aktivně zúčastníte hlasování",
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
    "loc_submit_poll_4": "Zahájit hlasování",
    "loc_submit_poll_5": "Ukončit schůzi",
    "loc_submit_poll_6": "Ukončit",
    "loc_submit_poll_7": "Vyberte limit",
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
    "loc_settings_block_2": "Vyberte jazyk",
    "loc_settings_block_3": "Odeslat soubor s výsledky po každém hlasování",
    "loc_settings_block_4": "Ano",
    "loc_settings_block_5": "Ne",
    "loc_user_settings_1": "Nastavení Bota",
    "loc_user_settings_2": "Nastavení se použije pro schůzi, kterou založíte v kterémkoli Prostoru. Nastavení můžete později změnit tím, že upravíte tento formulář a uložíte změny. Dělejte to před začátkem schůze.",
    "loc_user_settings_3": "Uložit",
    "loc_room_settings_1": "Nastaveni Bota",
    "loc_room_settings_2": "Nastavení se použije pro schůzi, kterou založíte v tomto Prostoru. Nastavení můžete později změnit tím, že upravíte tento formulář a uložíte změny. Dělejte to před začátkem schůze.",
    "loc_room_settings_3": "Ukožit",
    "loc_act_start_end_meeting_1": "ukončit",
    "loc_act_start_end_meeting_2": "zahájit",
    "loc_act_start_end_meeting_3": "V Prostoru **{}** může schůzi {} pouze moderátor. Domluvte se s ním. Kdo je moderátorem je vidět v seznamu členů Prostoru.",
    "loc_act_start_end_meeting_4": "Výsledky ke stažení.",
    "loc_publish_poll_results_1": "jméno",
    "loc_publish_poll_results_2": "pro",
    "loc_publish_poll_results_3": "proti",
    "loc_publish_poll_results_4": "zdržel se",
    "loc_publish_poll_results_5": "Výsledky ke stažení.",
    "loc_publish_poll_results_6": "volba",
    "loc_1_1_welcome_1": """
Dobrý den, jsem BOT pro řízení hlasování ve Webex Teams Prostoru (Space). Vše se odehrává pomocí formulářů, které vám budu posílat.

Přidejte mě do Prostoru, ve kterém chcete hlasovat.
"""
}

EN_US = {
    "loc_default_form_msg": "This is a form. It can be displayed in a Webex app or web client.",
    "loc_bot_welcome_1": "Welcome to the Voting Bot",
    "loc_bot_welcome_2": "Please start a new meeting",
    "loc_bot_welcome_3": "Start a meeting",
    "loc_bot_welcome_4": "Meeting name",
    "loc_bot_welcome_5": "Type the name",
    "loc_bot_welcome_6": "Start",
    "loc_poll_block_1": "Voting",
    "loc_poll_block_2": "Topic",
    "loc_poll_block_3": "Type the topic",
    "loc_poll_block_4": "Time limit",
    "loc_poll_block_5": "minute",
    "loc_poll_block_6": "minutes",
    "loc_poll_block_7": "Start voting",
    "loc_poll_block_8": "Select limit",
    "loc_next_poll_block_1": "Next voting",
    "loc_end_meeting_block_1": "End meeting",
    "loc_end_meeting_block_2": "End",
    "loc_start_meeting_1": "Meeting",
    "loc_start_meeting_2": "started",
    "loc_start_meeting_3": "started the meeting",
    "loc_start_meeting_4": "Click the",
    "loc_start_meeting_5": "Present",
    "loc_start_meeting_6": "button. Otherwise your presence will be recorded from the moment you cast your first vote",
    "loc_start_meeting_7": "Present",
    "loc_start_meeting_8": "Voting",
    "loc_start_meeting_9": "End voting",
    "loc_start_meeting_10": "End",
    "loc_end_meeting_1": "Meeting ended",
    "loc_end_meeting_2": "ended the meeting",
    "loc_end_meeting_3": "Start a new meeting",
    "loc_end_meeting_4": "Meeting name",
    "loc_end_meeting_5": "Type the name",
    "loc_end_meeting_6": "Start",
    "loc_submit_poll_1": "Topic",
    "loc_submit_poll_2": "Type the topic",
    "loc_submit_poll_3": "Time limit",
    "loc_submit_poll_4": "Start voting",
    "loc_submit_poll_5": "End meeting",
    "loc_submit_poll_6": "End",
    "loc_submit_poll_7": "Select limit",
    "loc_poll_template_1": "started the voting",
    "loc_poll_template_2": "Voting topic",
    "loc_poll_template_3": "Time limit",
    "loc_poll_template_4": "Yea",
    "loc_poll_template_5": "Nay",
    "loc_poll_template_6": "Abstain",
    "loc_poll_results_1": "voting results",
    "loc_poll_results_2": "Yea",
    "loc_poll_results_3": "Nay",
    "loc_poll_results_4": "Abstained",
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
    "loc_room_settings_3": "Save",
    "loc_act_start_end_meeting_1": "start",
    "loc_act_start_end_meeting_2": "end",
    "loc_act_start_end_meeting_3": "Only a moderator of the **{}** Space can {} the meeting. Ask him please. Moderator list is available in People list in the Space.",
    "loc_act_start_end_meeting_4": "Results for download.",
    "loc_publish_poll_results_1": "name",
    "loc_publish_poll_results_2": "yea",
    "loc_publish_poll_results_3": "nay",
    "loc_publish_poll_results_4": "abstained",
    "loc_publish_poll_results_5": "Results for download.",
    "loc_publish_poll_results_6": "vote",
    "loc_1_1_welcome_1": """
Hello, I am a Bot for conducting voting in a Webex Space. All is handled using forms I'm going to send you.

Please add me to a Space in which you want to run the voting.
"""}

# add the previously defined language constant to make it available for the Bot
LOCALES = {
    "cs_CZ": CS_CZ,
    "en_US": EN_US
}
