#!/usr/bin/env python3

import os
import sys
import re
import uuid
import logging
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from urllib.parse import urlparse, urlunparse, quote, parse_qsl, urlencode

from distutils.util import strtobool

from webexteamssdk import WebexTeamsAPI, ApiError, AccessToken
webex_api = WebexTeamsAPI()

from ddb_single_table_obj import DDB_Single_Table

import json, requests
from datetime import datetime, timedelta, timezone
import time
from flask import Flask, request, redirect, url_for, make_response
import io
import csv
from unidecode import unidecode
import xlsxwriter

from zappa.asynchronous import task

import concurrent.futures
import signal

import bot_buttons_cards as bc

from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb import types

DEFAULT_AVATAR_URL= "http://bit.ly/SparkBot-512x512"
# identification mapping in DB between form and submitted data
DEFAULT_POLL_LIMIT = 20
PUBLISH_PART_RESULTS = False

FORM_DATA_MAP = {
    "WELCOME_FORM": "END_MEETING_DATA",
    "START_MEETING_FORM": "START_MEETING_DATA",
    "END_MEETING_FORM": "END_MEETING_DATA",
    "POLL_FORM": "POLL_DATA",
    "POLL_RESULTS": "START_MEETING_DATA"
}

# type of form data to be saved in database
FORM_DATA_TO_SAVE = ["START_MEETING_DATA", "POLL_DATA"]

flask_app = Flask(__name__)
flask_app.config["DEBUG"] = True
requests.packages.urllib3.disable_warnings()

# threading part
thread_executor = concurrent.futures.ThreadPoolExecutor()

logger = logging.getLogger()

ddb = None
avatar_url = DEFAULT_AVATAR_URL
webhook_url = None
bot_name = None
bot_email = None
bot_id = None

"""
bot flow/events

1. BOT added to a Space
    * 1-1 Space
        - send message with a instructions to invite to a group Space
    * group Space
        - send "meeting start" card
    
2. "start meeting" clicked
    * send a card with options:
        - presence confirmation
        - start poll
        - end current poll
        - end meeting
    
3. presence actions
    - "present" clicked - record a user id in the database, info: space_id, meeting_id (new_meeting message id), user_id, timestamp
    - "end meeting" clicked - record all users not present
    
4. "open new poll"  actions:
    - "start poll" clicked - create a "poll" card, send it to the space, after message sent confirmed (received back), start the timer for poll close

5. "poll" card actions:
    - button clicked - record user's response, if a user is not present (didn't click "present" at start), he's recorded as present for the rest of the meeting
    - poll timer ended - delete the original "poll" card from the space, post "poll results", post poll results CSV file
    
6. "end meeting":
    - send a card with end meeting indication and a button to start a new meeting
    - send poll summary in XLS format
"""

"""
Finite state machine (FSM) section
This part controls the Bot's events
"""
@task
def fsm_handle_event(room_id, event_name, args_dict={}):
    """act upon FSM event
    each FSM action function will be called with arguments(room_id, event_name, args_dict)
    the action function can return a new state, in that case the "target state" from the FSM
    definition is ignored and the new state is set instead
    
    arguments:
    room_id -- room id to which the state is related
    event_name -- name of the event
    args_dict -- dict of additional arguments related to the event
    """
    flask_app.logger.debug("FSM event {}, roomId: {}".format(event_name, room_id))
    init_globals()
    current_state = get_current_state(room_id)
    for fsm_state, fsm_event, fsm_action, fsm_target_state in MEETING_FSM:
        if (fsm_state == current_state or fsm_state == "any_state") and fsm_event == event_name:
            if fsm_target_state == "same_state":
                fsm_target_state = current_state
            flask_app.logger.debug("FSM transition {} -> {}, event: {}, function: {}".format(current_state, fsm_target_state, event_name, fsm_action.__name__))

            # event state is saved before the action to avoid duplicate events in case the action takes a long time (includes time.sleep())
            save_current_state(room_id, fsm_target_state)
            new_state = fsm_action(room_id, event_name, args_dict)
            if new_state is not None:
                save_current_state(room_id, new_state)
                flask_app.logger.debug("FSM transition {} -> {}, event: {}, function: {}".format(current_state, new_state, event_name, fsm_action.__name__))
            break
    else:
        flask_app.logger.debug("Unhandled FSM event \"{}\"".format(event_name))
            
def get_current_state(room_id):
    """get current FSM state
    
    arguments:
    room_id -- room id to which the state is related
    """
    state = None
    state_res = ddb.get_db_record(room_id, "FSM_STATE")
    if state_res:
        state = state_res.get("pvalue")
    flask_app.logger.debug("FSM current state: {}, roomId: {}".format(state, room_id))
    return state
    
def save_current_state(room_id, state):
    """save current FSM state
    
    arguments:
    room_id -- room id to which the state is related
    state -- state value
    """
    ddb.save_db_record(room_id, "FSM_STATE", state)
    flask_app.logger.debug("FSM save state: {}, roomId".format(state, room_id))
    
def clear_current_state(room_id):
    """clear FSM state
    
    arguments:
    room_id -- room id to which the state is related
    """
    ddb.delete_db_record(room_id, "FSM_STATE")
                
def act_added_to_space(room_id, event_name, args_dict):
    """Bot was added to the Space"""
    attach = [bc.wrap_form(bc.WELCOME_TEMPLATE)]
    form_type = "WELCOME_FORM"
    send_message({"roomId": room_id}, "welcome form", attachments=attach, form_type=form_type)
    
def act_removed_from_space(room_id, event_name, args_dict):
    """Bot was removed from the Space"""
    flask_app.logger.debug("removed from space {}".format(room_id))

def act_start_end_meeting(room_id, event_name, args_dict):
    """Meeting started/ended - sent the proper card"""
    try:
        flask_app.logger.debug("{} meeting args: {}".format(event_name, args_dict))
        
        # TODO remove previous start/end meeting form
        
        moderators = get_moderators(room_id)
        
        if moderators:
            person_id = args_dict["personId"]
            if person_id not in moderators:
                flask_app.logger.debug("{} is not a moderator in the roomId {}, ignorng start/end request".format(person_id, room_id))
                room_details = webex_api.rooms.get(room_id)
                room_name = room_details.title
                action_name = "ukončit"
                next_state = "MEETING_ACTIVE"
                if event_name == "ev_start_meeting":
                    action_name = "zahájit"
                    next_state = "MEETING_INACTIVE"
                send_message({"toPersonId": person_id}, "V Prostoru **{}** může schůzi {} pouze moderátor. Domluvte se s ním. Kdo je moderátorem je vidět v seznamu členů Prostoru.".format(room_name, action_name))
                
                return next_state
        
        inputs = args_dict.get("inputs", {})

        meeting_info = {
            "subject": inputs.get("meeting_subject", "")
        }
        
        timestamp = create_timestamp()
        if event_name == "ev_start_meeting":
            template = bc.START_MEETING_TEMPLATE
            form_type = "START_MEETING_FORM"
            meeting_status = "MEETING_START"
        else:
            template = bc.END_MEETING_TEMPLATE
            form_type = "END_MEETING_FORM"
            meeting_status = "MEETING_END"
            
            clear_meeting_presence(room_id)
        
        flask_app.logger.debug("Saving meeting \"{}\"status {}, timestamp {}".format(meeting_info["subject"], meeting_status, timestamp))
        ddb.save_db_record(room_id, timestamp, meeting_status, **meeting_info)
            
        user_info = webex_api.people.get(args_dict["personId"])
        form = nested_replace(template, "display_name", user_info.displayName)
        form = nested_replace(form, "meeting_subject", meeting_info["subject"])
        attach = [bc.wrap_form(form)]
        msg_id = send_message({"roomId": room_id}, "{} meeting form".format(event_name), attachments=attach, form_type=form_type)
        
        if event_name == "ev_end_meeting":
            results_items, meeting_name = get_last_meeting_results(room_id)
            if len(results_items) > 0:
                my_url = get_my_url()
                if my_url:
                    now = datetime.now()
                    file_name = now.strftime("%Y_%m_%d_%H_%M_")
                    
                    # res_url = my_url + url_for("last_csv_summary", room_id = room_id, filename = file_name)
                    res_url = my_url + "/lastcsvsummary/{}?filename={}".format(room_id, file_name)
                    flask_app.logger.debug("URL for summary CSV download: {}".format(res_url))
                    
                    webex_api.messages.create(roomId = room_id, parentId = msg_id, markdown = "Výsledky ke stažení.", files = [res_url])
    
    except ApiError as e:
        flask_app.logger.error("{} meeting form create failed: {}.".format(event_name, e))
        
def get_moderators(room_id):
    """return a list of Space moredators
    
    arguments:
    room_id -- id of the Space
    """
    members = webex_api.memberships.list(roomId = room_id)
    moderators = []
    for member in members:
        if member.isModerator:
            moderators.append(member.personId)
            
    return moderators
        
def clear_meeting_presence(room_id):
    """clear presence status of all users in the Space
    
    arguments:
    room_id -- id of the Space
    """
    present_users = get_present_users(room_id)
    flask_app.logger.debug("clear presence status for roomId: {}".format(room_id))
    for user_id in present_users:
        set_presence(room_id, user_id, False)
        
def get_present_users(room_id):
    """return list of user ids of users who set their presence in the Space
    
    arguments:
    room_id -- id of the Space
    """
    present_list = ddb.query_db_record(room_id, "PRESENT")
    present_users = []
    for prs in present_list:
        status = prs.get("status", False)
        if status:
            present_users.append(prs["sk"])
        
    return present_users

def act_start_poll(room_id, event_name, args_dict):
    """start the poll, send the poll card"""
    inputs = args_dict.get("inputs", {})
    subject = inputs.get("poll_subject")
    time_limit = inputs.get("time_limit")
    form_type = "POLL_FORM"
    try:
        user_info = webex_api.people.get(args_dict["personId"])
        form = nested_replace(bc.POLL_TEMPLATE, "display_name", user_info.displayName)
        form = nested_replace(form, "poll_subject", subject)
        form = nested_replace(form, "time_limit", time_limit)
        attach = [bc.wrap_form(form)]
        message_id = send_message({"roomId": room_id}, "{} meeting form".format(event_name), attachments=attach, form_type=form_type, form_params=inputs)
        
        inputs["form_id"] = message_id
        
        save_last_poll_state(room_id, "RUNNING", inputs)
        request_poll_end(room_id, inputs)
            
    except ApiError as e:
        flask_app.logger.error("{} meeting form create failed: {}.".format(event_name, e))
        
def save_last_poll_state(room_id, state, inputs):
    """save poll state in order to be able to handle both automated and manual poll end"""
    flask_app.logger.debug("Saving poll state \"{}\" in space {}, inputs: {}".format(state, room_id, inputs))
    ddb.save_db_record(room_id, "POLL_STATE", state, inputs = inputs)
    
def get_last_poll_state(room_id):
    """get the poll state"""
    poll_state_res = ddb.get_db_record(room_id, "POLL_STATE")
    state = poll_state_res.get("pvalue", "UNKNOWN")
    inputs = poll_state_res.get("inputs", {})
    flask_app.logger.debug("Last poll state in space {}: {}, {}".format(room_id, state, inputs))
    
    return state, inputs
        
@task
def request_poll_end(room_id, inputs):
    """automated poll end"""
    delay = int(inputs.get("time_limit", DEFAULT_POLL_LIMIT))
    subject = inputs.get("poll_subject")
    form_id = inputs.get("form_id")
    flask_app.logger.debug("ready for poll \"{}\" form finish {}".format(subject, form_id))
    time.sleep(delay)
    flask_app.logger.debug("ending poll \"{}\" {}".format(subject, form_id))
    fsm_handle_event(room_id, "ev_end_poll", inputs)
        
def act_end_poll(room_id, event_name, args_dict):
    """end poll both automatically and manually"""
    flask_app.logger.debug("end poll args: {}".format(args_dict))
    # init_globals() # make sure ddb is available
    
    poll_state, inputs = get_last_poll_state(room_id)
    subject = inputs.get("poll_subject")
    form_id = inputs.get("form_id")
    args_id = args_dict.get("form_id", None)
    if args_id and args_id != form_id:
        flask_app.logger.info("running form id and ending form id do not match, no action {} != {}". format(args_id, form_id))
        return "POLL_RUNNING" # keep the poll running
        
    if poll_state == "RUNNING":
        flask_app.logger.debug("deleting poll \"{}\" form {}".format(subject, form_id))
        try:
            webex_api.messages.delete(form_id)

            publish_poll_results(room_id, form_id, subject)

        except ApiError as e:
            flask_app.logger.error("message {} delete failed: {}.".format(form_id, e))
        
        save_last_poll_state(room_id, "ENDED", args_dict)
    else:
        flask_app.logger.debug("poll \"{}\" - {} not running (state: {})".format(subject, form_id, poll_state))
        
def publish_poll_results(room_id, form_id, subject):
    """send card with poll results, save results to the database"""
    flask_app.logger.debug("publishing poll \"{}\" results, form id: {}".format(subject, form_id))
    poll_results = ddb.query_db_record(form_id, "POLL_DATA")
    yea_res = []
    nay_res = []
    abstain_res = []
    active_users = []
    vote_results = []
    for res in poll_results:
        vote = res.get("vote")
        voter_id = res["sk"]
        active_users.append(voter_id)
        voter_data = webex_api.people.get(voter_id)
        if vote == "yea":
            yea_res.append(voter_data.displayName)
            vote_results.append({"jmeno": voter_data.displayName, "volba": "pro"})
        elif vote == "nay":
            nay_res.append(voter_data.displayName)
            vote_results.append({"jmeno": voter_data.displayName, "volba": "proti"})
        elif vote == "abstain":
            abstain_res.append(voter_data.displayName)
            vote_results.append({"jmeno": voter_data.displayName, "volba": "zdrzel se"})
            
    present_users = get_present_users(room_id)
    passive_users = list(set(present_users).difference(set(active_users)))
    for user_id in passive_users:
        voter_data = webex_api.people.get(user_id)
        abstain_res.append(voter_data.displayName)
        vote_results.append({"jmeno": voter_data.displayName, "volba": "zdrzel se"})
        
    voter_columns = {
        "type": "ColumnSet",
        "columns": []
    }

    for voters in (yea_res, nay_res, abstain_res):
        voters.sort(key=lambda x: x.split(" ")[-1]) # sort by last name
        voter_columns["columns"].append(create_result_column(voters))
    vote_results.sort(key=lambda x: x["jmeno"].split(" ")[-1])
    
    rslt = {
        "vote_results": vote_results,
        "subject": subject,
        "timestamp": create_timestamp()
    }
    ddb.save_db_record(room_id, form_id, "RESULTS", **rslt)
        
    poll_result_attachment = nested_replace(bc.POLL_RESULTS_TEMPLATE, "poll_subject", subject)
    poll_result_attachment = nested_replace(poll_result_attachment, "yea_count", len(yea_res))
    poll_result_attachment = nested_replace(poll_result_attachment, "nay_count", len(nay_res))
    poll_result_attachment = nested_replace(poll_result_attachment, "abstain_count", len(abstain_res))
    poll_result_attachment["body"].append(voter_columns)
    poll_result_attachment["body"].append(bc.NEXT_POLL_BLOCK) 
    poll_result_attachment["body"].append(bc.END_MEETING_BLOCK) 
    
    msg_id = send_message({"roomId": room_id}, "{} poll results".format(subject), attachments=[bc.wrap_form(poll_result_attachment)], form_type="POLL_RESULTS")
    
    # publish results after each poll?
    if PUBLISH_PART_RESULTS and len(vote_results) > 0:
        my_url = get_my_url()
        if my_url:
            result_name = unidecode(subject).lower().replace(" ", "_")
            now = datetime.now()
            file_name = now.strftime("%Y_%m_%d_%H_%M_") + result_name
            
            # res_url = my_url + url_for("csv_results", room_id = room_id, form_id = form_id, filename = file_name)
            res_url = my_url + "/csvresults/{}/{}?filename={}".format(room_id, form_id, file_name)
            flask_app.logger.debug("URL for CSV download: {}".format(res_url))
            
            webex_api.messages.create(roomId = room_id, parentId = msg_id, markdown = "Výsledky ke stažení.", files = [res_url])
    
def create_result_column(result):
    """create an individual result column for the card"""
    column = []
    for res in result:
        column.append(nested_replace(bc.RESULT_PARTICIPANT_TEMPLATE, "display_name", res))
        
    column_result = {
        "type": "Column",
        "width": "stretch",
        "items": column
    }
                
    flask_app.logger.debug("result column: {}".format(column_result))
        
    return column_result
    
def act_presence(room_id, event_name, args_dict):
    """presence indication"""
    message_id = args_dict.get("messageId")
    person_id = args_dict.get("personId")
    set_presence(room_id, person_id, True)
    
def set_presence(room_id, person_id, status):
    """save user's presence in the Space id (room_id)"""
    status_data = {"status": status}
    ddb.save_db_record(room_id, person_id, "PRESENT", **status_data)
    flask_app.logger.debug("Presence status for user {} set to {}, roomId: {}".format(person_id, status, room_id))    
        
def act_poll_data(room_id, event_name, args_dict):
    """poll click received from a user"""
    message_id = args_dict.get("messageId") # webhook["data"]["messageId"]
    person_id = args_dict.get("personId") # webhook["data"]["personId"]
    set_presence(room_id, person_id, True)
    form_saved = save_form_data(message_id, person_id, args_dict, "POLL_DATA")
            
MEETING_FSM = [
# current_state   event     action    target_state
# "any_state" - execute the event action no matter of the state
# "same_state" - keep the state the same
[None, "ev_added_to_space", act_added_to_space, "WELCOME"],
["IDLE", "ev_added_to_space", act_added_to_space, "WELCOME"],
["any_state", "ev_added_to_space", act_added_to_space, "WELCOME"],
["WELCOME", "ev_start_meeting", act_start_end_meeting, "MEETING_ACTIVE"],
["MEETING_INACTIVE", "ev_start_meeting", act_start_end_meeting, "MEETING_ACTIVE"],
["MEETING_ACTIVE", "ev_presence", act_presence, "same_state"],
["POLL_RUNNING", "ev_presence", act_presence, "same_state"],
["any_state", "ev_end_meeting", act_start_end_meeting, "MEETING_INACTIVE"],
# ["any_state", "ev_start_poll", act_start_poll, "POLL_RUNNING"],
["MEETING_ACTIVE", "ev_start_poll", act_start_poll, "POLL_RUNNING"],
["POLL_RUNNING", "ev_poll_data", act_poll_data, "same_state"],
["POLL_RUNNING", "ev_end_poll", act_end_poll, "MEETING_ACTIVE"],
["any_state", "ev_removed_from_space", act_removed_from_space, "REMOVED"]
]

def create_timestamp():
    """time stamp in UTC (ISO 8601) format - used as secondary key in some DB operations"""
    return datetime.utcnow().isoformat()[:-3]+'Z'
    
def parse_timestamp(time_str):
    """create datetime object from UTC (ISO 8601) string"""
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))

def nested_replace( structure, original, new):
    """replace {{original}} wrapped strings with new value
    use recursion to walk the whole sructure
    
    arguments:
    structure -- input dict / list / string
    original -- string to search for
    new -- will replace every occurence of {{original}}
    """
    if type(structure) == list:
        return [nested_replace( item, original, new) for item in structure]

    if type(structure) == dict:
        return {key : nested_replace(value, original, new)
                     for key, value in structure.items() }

    if type(structure) == str:
        return structure.replace("{{"+original+"}}", str(new))
    else:
        return structure
        
def get_my_url():
    """workaround to get the full Bot URL in case the application context is not available"""
    my_webhooks = webex_api.webhooks.list(max = 1)
    if my_webhooks:
        for wh in my_webhooks:
            my_url = wh.targetUrl
            break
        myUrlParts = urlparse(my_url)
        url = secure_scheme(myUrlParts.scheme) + "://" + myUrlParts.netloc + myUrlParts.path
        
        return url

def create_webhook(target_url):
    """create a set of webhooks for the Bot
    webhooks are defined according to the resource_events dict
    
    arguments:
    target_url -- full URL to be set for the webhook
    """    
    flask_app.logger.debug("Create new webhook to URL: {}".format(target_url))
    
    webhook_name = "Webhook for Bot {}".format(bot_email)
    resource_events = {
        "messages": ["created"],
        "memberships": ["created", "deleted"],
        "attachmentActions": ["created"]
    }
    status = None
        
    try:
        check_webhook = webex_api.webhooks.list()
        for webhook in check_webhook:
            flask_app.logger.debug("Deleting webhook {}, '{}', App Id: {}".format(webhook.id, webhook.name, webhook.appId))
            try:
                if not flask_app.testing:
                    webex_api.webhooks.delete(webhook.id)
            except ApiError as e:
                flask_app.logger.error("Webhook {} delete failed: {}.".format(webhook.id, e))
    except ApiError as e:
        flask_app.logger.error("Webhook list failed: {}.".format(e))
        
    for resource, events in resource_events.items():
        for event in events:
            try:
                if not flask_app.testing:
                    webex_api.webhooks.create(name=webhook_name, targetUrl=target_url, resource=resource, event=event)
                status = True
                flask_app.logger.debug("Webhook for {}/{} was successfully created".format(resource, event))
            except ApiError as e:
                flask_app.logger.error("Webhook create failed: {}.".format(e))
            
    return status

def group_info(bot_name):
    return "Nezapomeňte, že je třeba mne oslovit '@{}'".format(bot_name)

def greetings(personal=True):
    
    greeting_msg = """
Dobrý den, jsem BOT pro řízení hlasování ve Webex Teams Prostoru (Space). Vše se odehrává pomocí formulářů, které vám budu posílat.

Přidejte mě do Prostoru, ve kterém chcete hlasovat.
"""
    if not personal:
        greeting_msg += " " + group_info(bot_name)

    return greeting_msg

def help_me(personal=True):

    greeting_msg = """
Dummy help.
"""
    if not personal:
        greeting_msg += group_info(bot_name)

    return greeting_msg

def is_room_direct(room_id):
    try:
        res = webex_api.rooms.get(room_id)
        return res.type == "direct"
    except ApiError as e:
        flask_app.logger.error("Room info request failed: {}".format(e))
        return False

def save_form_info(creator_id, form_data_id, form_type, params={}):
    return ddb.save_db_record(creator_id, form_data_id, form_type, **params)
    
def get_form_info(form_data_id):
    return ddb.get_db_records_by_secondary_key(form_data_id)[0]
    
def delete_form_info(form_data_id):
    return ddb.delete_db_records_by_secondary_key(form_data_id)
    
def save_form_data(primary_key, secondary_key, registration_data, data_type, **kwargs):
    inputs = registration_data.get("inputs", {})
    optional_data = {**inputs, **kwargs}
    return ddb.save_db_record(primary_key, secondary_key, data_type, **optional_data)
    
def get_form_data(form_data_id):
    return ddb.get_db_record_list(form_data_id)
    
def delete_form_data_for_user(form_id, user_id):
    return ddb.delete_db_record(form_id, user_id)
    
def secure_scheme(scheme):
    return re.sub(r"^http$", "https", scheme)

def send_message(destination, markdown, attachments=[], form_type=None, form_params={}):
    try:
        flask_app.logger.debug("Send to destination: {}\n\nmarkdown: {}\n\nattach: {}".format(destination, markdown, attachments))
        res_msg = webex_api.messages.create(**destination, markdown=markdown, attachments=attachments)
        flask_app.logger.debug("Message created: {}".format(res_msg.json_data))
        if len(attachments) > 0 and form_type is not None:
            save_form_info(bot_id, res_msg.id, form_type, form_params) # sender is the owner
        else:
            flask_app.logger.debug("Not saving, attach len: {}, form type: {}".format(len(attachments), form_type))
            
        return res_msg.id
    except ApiError as e:
        flask_app.logger.error("Message create failed: {}.".format(e))
        
def init_globals():
    global ddb

    ddb = DDB_Single_Table()
    flask_app.logger.debug("initialize DDB object {}".format(ddb))

# Flask part of the code

"""
1. initialize database table if needed
2. start event checking thread
"""
@flask_app.before_request
def before_request():
    global bot_email, bot_name, bot_id, avatar_url, ddb
    
    try:
        me = webex_api.people.me()
        bot_email = me.emails[0]
        bot_name = me.displayName
        bot_id = me.id
        avatar_url = me.avatar
    except ApiError as e:
        avatar_url = DEFAULT_AVATAR_URL
        flask_app.logger.error("Status code: {}, {}".format(e.status_code, e.message))

    if ("@sparkbot.io" not in bot_email) and ("@webex.bot" not in bot_email):
        flask_app.logger.error("""
You have provided access token which does not belong to a bot ({}).
Please review it and make sure it belongs to your bot account.
Do not worry if you have lost the access token.
You can always go to https://developer.ciscospark.com/apps.html 
URL and generate a new access token.""".format(bot_email))

    init_globals()
    
"""
Main function which handles the webhook events. It reacts both on messages and button&card events

Look at the 'msg +=' for workflow explanation
"""

# @task
def handle_webhook_event(webhook):
    action_list = []
    if webhook["data"].get("personEmail") != bot_email:
        flask_app.logger.info(json.dumps(webhook))
        
    msg = ""
    attach = []
    target_dict = {"roomId": webhook["data"]["roomId"]}
    form_type = None
    out_messages = [] # additional messages apart of the standard response
        
# handle Bot's membership events (Bot added/removed from Space or 1-1 communication)
    if webhook["resource"] == "memberships":
        if webhook["data"]["personId"] == bot_id:
            if webhook["event"] == "created":
                personal_room = is_room_direct(webhook["data"]["roomId"])
                if personal_room:
                    flask_app.logger.debug("I was invited to a new 1-1 communication")
                    msg = markdown=greetings(personal_room)
                    action_list.append("invited to a new 1-1 communication")
                else:
                    flask_app.logger.debug("I was invited to a new group Space")
                    fsm_event = "ev_added_to_space"
                    # msg = "Odešle se nápověda a formulář pro zahájení schůze."
                    action_list.append("invited to a group Space")
                    fsm_handle_event(webhook["data"]["roomId"], "ev_added_to_space")
            elif webhook["event"] == "deleted":
                flask_app.logger.info("I was removed from a Space")
                action_list.append("bot removed from a Space")
                fsm_handle_event(webhook["data"]["roomId"], "ev_removed_from_space")
            else:
                flask_app.logger.info("unhandled membership event '{}'".format(webhook["event"]))

        if msg != "" or len(attach) > 0:
            out_messages.append({"message": msg, "attachments": attach, "target": target_dict, "form_type": form_type})
        
# handle text messages
    elif webhook["resource"] == "messages":
        if webhook["data"]["personEmail"] == bot_email:
            flask_app.logger.debug("Ignoring my own message")
            # TODO check if the message is a poll form, start timer for the poll
        else:
            in_msg = webex_api.messages.get(webhook["data"]["id"])
            in_msg_low = in_msg.text.lower()
            in_msg_low = in_msg_low.replace(bot_name.lower() + " ", "") # remove bot"s name from message test to avoid command conflict
            myUrlParts = urlparse(request.url)

            if "help" in in_msg_low:
                personal_room = is_room_direct(webhook["data"]["roomId"])
                msg = help_me(personal_room)
                action_list.append("help created")
                
            if msg != "" or len(attach) > 0:
                out_messages.append({"message": msg, "attachments": attach, "target": target_dict, "form_type": form_type})
                
# handle buttons&cards events
# the event information contains the message ID in which the card was originally posted
# so in order to follow the context the message ID has to be stored when the card is posted to a space
# see 'save_form_info()'
# this way we can not only gather the card data but also get the information to which card the user is responding
    elif webhook["resource"] == "attachmentActions":
        try:
            in_attach = webex_api.attachment_actions.get(webhook["data"]["id"])
            in_attach_dict = in_attach.to_dict()
            flask_app.logger.debug("Form received: {}".format(in_attach_dict))
            # flask_app.logger.debug("Form metadata: \nApp Id: {}\nMsg Id: {}\nPerson Id: {}".format(webhook["appId"], webhook["data"]["messageId"], webhook["data"]["personId"]))
            action_list.append("form received")
            in_attach_dict["orgId"] = webhook["orgId"] # orgId is present only in original message, not in attachement
            
            parent_record = ddb.get_db_records_by_secondary_key(webhook["data"]["messageId"])[0]
            flask_app.logger.debug("Parent record: {}".format(parent_record))
            form_type = parent_record.get("pvalue")
            form_data_type = FORM_DATA_MAP.get(form_type)
            flask_app.logger.debug("Received form type: {} -> {}".format(form_type, form_data_type))
            form_params = {}
                
            fsm_event = detect_form_event(form_type, in_attach_dict)
            fsm_handle_event(webhook["data"]["roomId"], fsm_event, in_attach_dict)
            
        except ApiError as e:
            flask_app.logger.error("Form read failed: {}.".format(e))
            action_list.append("form read failed")
                        
    if len(out_messages) > 0:
        for msg_dict in out_messages:
            target_dict = msg_dict["target"]
            msg = msg_dict["message"]
            attach = msg_dict.get("attachments", [])
            form_type = msg_dict.get("form_type", "UNKNOWN_FORM")
            form_params = msg_dict.get("form_params", {})
            send_message(target_dict, msg, attach, form_type, form_params)

    return json.dumps(action_list)
    
def detect_form_event(form_type, attachment_data):
    inputs = attachment_data.get("inputs", {})
    event = "ev_none"
    if form_type in ["WELCOME_FORM", "END_MEETING_FORM"]:
        event = "ev_start_meeting"
    elif form_type in ["START_MEETING_FORM", "POLL_RESULTS"]:
        button_pressed = inputs.get("action", None)
        if button_pressed == "present":
            event = "ev_presence"
        elif button_pressed == "start_poll":
            event = "ev_start_poll"
        elif button_pressed == "end_poll":
            event = "ev_end_poll"
        elif button_pressed == "end_meeting":
            event = "ev_end_meeting"
    elif form_type == "SUBMIT_POLL_FORM":
        pass
    elif form_type == "POLL_FORM":
        event = "ev_poll_data"
        
    return event
    
"""
Bot setup. Used mainly for webhook creation and gathering a dynamic Bot URL.
"""

@flask_app.route("/", methods=["GET", "POST"])
def spark_webhook():
    if request.method == "POST":
        webhook = request.get_json(silent=True)
        
        handle_webhook_event(webhook)        
    elif request.method == "GET":
        message = "<center><img src=\"{0}\" alt=\"{1}\" style=\"width:256; height:256;\"</center>" \
                  "<center><h2><b>Congratulations! Your <i style=\"color:#ff8000;\">{1}</i> bot is up and running.</b></h2></center>".format(avatar_url, bot_name)
                  
        message += "<center><b>I'm hosted at: <a href=\"{0}\">{0}</a></center>".format(request.url)
        if webhook_url is None:
            res = create_webhook(request.url)
            if res is True:
                message += "<center><b>New webhook created sucessfully</center>"
            else:
                message += "<center><b>Tried to create a new webhook but failed, see application log for details.</center>"

        return message
        
    flask_app.logger.debug("Webhook handling done.")
    return "OK"
    
@flask_app.route("/csvresults/<room_id>/<form_id>", methods=["GET"])
def csv_results(room_id, form_id):
    results = ddb.get_db_record(room_id, form_id)
    if results is None:
        return ""

    csv_list = results.get("vote_results")
    if csv_list is None:
        return ""
        
    file_name = request.args.get("filename", "export")
        
    keys = csv_list[0].keys()
    si = io.StringIO()
    cw = csv.DictWriter(si, keys)
    cw.writeheader()
    cw.writerows(csv_list)
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename={}.csv".format(file_name)
    output.headers["Content-type"] = "text/csv"
    return output
    
@flask_app.route("/lastcsvsummary/<room_id>", methods=["GET"])
def last_csv_summary(room_id):
    """
    1. get meeting start and end
    2. get all poll results, sort by date
    3. get all unique users, sort by last name
    4. create header with "name, poll_1, poll_2,..."
    5. walk the results, create a list for each user line, empty string if user was not present
    """
    
    try:
        results_items, meeting_name = get_last_meeting_results(room_id)
        
        if len(results_items) == 0:
            flask_app.logger.debug("empty results")
            return "" # return not found
            
        results_items.sort(key=lambda x: x["timestamp"])
            
        user_list = []
        subject_list = []
        for poll_res in results_items:
            vote_results = poll_res.get("vote_results", [])
            user_list += get_name_from_results(vote_results)
            subject_list.append(poll_res["subject"])
            
        user_list = list(set(user_list)) # get unique names
        user_list.sort(key=lambda x: x.split(" ")[-1]) # sort by last name
        flask_app.logger.debug("got user list: {}".format(user_list))
        
        header_list = ["jmeno"] + subject_list
        complete_results = []
        for user in user_list:
            user_vote_list = [user]
            for poll_res in results_items:
                vote_results = poll_res.get("vote_results", [])
                user_vote_list.append(get_vote_for_user(vote_results, user))
                
            complete_results.append(user_vote_list)
            
        file_name = request.args.get("filename", "export")
            
        """
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(header_list)
        cw.writerows(complete_results)
        output = make_response(si.getvalue())
        """
        bi = io.BytesIO()
        workbook = xlsxwriter.Workbook(bi)
        worksheet = workbook.add_worksheet()
        worksheet.set_column(0, 0, 30)
        top_row_format = workbook.add_format({'bold': True})

        worksheet.write_row('A1', header_list, top_row_format)
        worksheet.autofilter(0, 1, len(complete_results)+1, len(header_list)-1)
        for row in range(0, len(complete_results)):
            worksheet.write_row('A'+str(row+2), complete_results[row])
        workbook.close()

        output = make_response(bi.getvalue())
        
        output.headers["Content-Disposition"] = "attachment; filename={}.xlsx".format(file_name + meeting_name)
        output.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return output
        
    except Exception as e:
        flask_app.logger.error("Last meeting CSV summary exception: {}".format(e))
        
    return ""
    
def get_last_meeting_results(room_id):
    now = create_timestamp()
    flask_app.logger.debug("Query results for timestamp {} and room_id {}".format(now, room_id))
    meeting_start_res = ddb.table.query(KeyConditionExpression=Key("pk").eq(room_id) & Key("sk").lt(now), FilterExpression=Attr("pvalue").eq("MEETING_START"), ScanIndexForward=False, Limit=5000)
    flask_app.logger.debug("Found meeting start: {}".format(meeting_start_res))
    meeting_end_res = ddb.table.query(KeyConditionExpression=Key("pk").eq(room_id) & Key("sk").lt(now), FilterExpression=Attr("pvalue").eq("MEETING_END"), ScanIndexForward=False, Limit=5000)
    flask_app.logger.debug("Found meeting end: {}".format(meeting_end_res))
    
    last_meeting_start = meeting_start_res["Items"][0]["sk"]
    last_meeting_end = meeting_end_res["Items"][0]["sk"]
    if last_meeting_end < last_meeting_start:
        last_meeting_end = now
        
    meeting_name = unidecode(meeting_start_res["Items"][0].get("subject", "")).lower().replace(" ", "_")
        
    results_res = ddb.table.query(KeyConditionExpression=Key("pk").eq(room_id), FilterExpression=Attr("pvalue").eq("RESULTS") & Attr("timestamp").lte(last_meeting_end) & Attr("timestamp").gte(last_meeting_start), ScanIndexForward=True)
    flask_app.logger.debug("Meeting results: {}".format(results_res))
    results_items = results_res.get("Items")
    
    return results_items, meeting_name
            
def get_name_from_results(vote_results):
    name_list = []
    for vote in vote_results:
        name = vote.get("jmeno")
        if name:
            name_list.append(name)
            
    return name_list
    
def get_vote_for_user(vote_results, user):
    for vote_item in vote_results:
        if vote_item["jmeno"] == user:
            return vote_item["volba"]
            
    return ""
    

"""
Startup procedure used to initiate @flask_app.before_first_request
"""

@flask_app.route("/startup")
def startup():
    return "Hello World!"
    
"""
Independent thread startup, see:
https://networklore.com/start-task-with-flask/
"""
def start_runner():
    def start_loop():
        not_started = True
        while not_started:
            logger.info('In start loop')
            try:
                r = requests.get('http://127.0.0.1:5050/startup')
                if r.status_code == 200:
                    logger.info('Server started, quiting start_loop')
                    not_started = False
                logger.debug("Status code: {}".format(r.status_code))
            except:
                logger.info('Server not yet started')
            time.sleep(2)

    logger.info('Started runner')
    thread_executor.submit(start_loop)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='count', help="Set logging level by number of -v's, -v=WARN, -vv=INFO, -vvv=DEBUG")
    
    args = parser.parse_args()
    if args.verbose:
        if args.verbose > 2:
            logging.basicConfig(level=logging.DEBUG)
        elif args.verbose > 1:
            logging.basicConfig(level=logging.INFO)
        if args.verbose > 0:
            logging.basicConfig(level=logging.WARN)
            
    flask_app.logger.info("Logging level: {}".format(logging.getLogger(__name__).getEffectiveLevel()))
    
    bot_identity = webex_api.people.me()
    flask_app.logger.info("Bot \"{}\"\nUsing database: {} - {}".format(bot_identity.displayName, os.getenv("DYNAMODB_ENDPOINT_URL"), os.getenv("DYNAMODB_TABLE_NAME")))
    
    start_runner()
    flask_app.run(host="0.0.0.0", port=5050, threaded=True)
