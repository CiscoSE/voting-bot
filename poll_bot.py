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
from settings import BotSettings

import json, requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
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
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

FORM_DATA_MAP = {
    "WELCOME_FORM": "END_MEETING_DATA",
    "START_MEETING_FORM": "START_MEETING_DATA",
    "END_MEETING_FORM": "END_MEETING_DATA",
    "POLL_FORM": "POLL_DATA",
    "POLL_RESULTS": "START_MEETING_DATA",
    "ROOM_SETTINGS_FORM": "ROOM_SETTINGS_DATA",
    "USER_SETTINGS_FORM": "USER_SETTINGS_DATA"
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
    each FSM action function will be called with arguments(room_id, event_name, settings, args_dict)
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
    
    settings = load_settings(room_id, event_name, args_dict)
    flask_app.logger.debug("Active settings: {}".format(settings.settings))
    
    for fsm_state, fsm_event, fsm_action, fsm_target_state in MEETING_FSM:
        if (fsm_state == current_state or fsm_state == "any_state") and fsm_event == event_name:
            if fsm_target_state == "same_state":
                fsm_target_state = current_state
            flask_app.logger.debug("FSM transition {} -> {}, event: {}, function: {}".format(current_state, fsm_target_state, event_name, fsm_action.__name__))

            # event state is saved before the action to avoid duplicate events in case the action takes a long time (includes time.sleep())
            save_current_state(room_id, fsm_target_state)
            new_state = fsm_action(room_id, event_name, settings, args_dict)
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
    
def load_settings(room_id, event_name, args_dict):
    """load space or user settings. User settings take precedens over space settings.
    
    arguments:
    room_id -- room id to which the settings is related
    event_name -- name of the events
    args_dict -- arguments passed to the event handler function
    """
    person_id = args_dict.get("personId")
    room_settings = BotSettings(db = ddb, settings_id = room_id)
    flask_app.logger.debug("Room settings {}stored, value: {}".format("not " if not room_settings.stored else "", room_settings.settings))
    if person_id is not None:
        person_settings = BotSettings(db = ddb, settings_id = person_id)
        flask_app.logger.debug("Person {} settings {}stored, value: {}".format(person_id, "not " if not person_settings.stored else "", person_settings.settings))
        if person_settings.stored and person_settings.settings.get("user_updated", False):
            room_settings.settings = person_settings.settings
            room_settings.save()
                
    return room_settings
                
def act_added_to_space(room_id, event_name, settings, args_dict):
    """handle the Bot-added-to-a-space event
    
    arguments:
    room_id -- room id to which the settings is related
    event_name -- name of the events
    settings -- current active settings (user- or space-level)
    args_dict -- arguments passed to the event handler function
    """
    """Bot was added to the Space"""
    person_id = args_dict["actorId"]
    person_settings = BotSettings(db = ddb, settings_id = person_id)
    flask_app.logger.debug("Person settings {}stored, value: {}".format("not " if not person_settings.stored else "", person_settings.settings))
    room_settings_available = False
    if not person_settings.stored: # no active user settings, let's ask in the space
        attach = [bc.wrap_form(bc.localize(bc.ROOM_SETTINGS_TEMPLATE, settings.settings["language"]))]
        form_type = "ROOM_SETTINGS_FORM"
        send_message({"roomId": room_id}, "settings form", attachments=attach, form_type=form_type)
        room_settings_available = True

    if not person_settings.settings["user_1_1"]: # user not yet in 1-1 communcation with the Bot
        attach = [bc.wrap_form(bc.localize(bc.USER_SETTINGS_TEMPLATE, settings.settings["language"]))]
        form_type = "USER_SETTINGS_FORM"
        send_message({"toPersonId": person_id}, "settings form", attachments=attach, form_type=form_type)
        person_settings.settings = {"user_1_1": True}
        person_settings.save()
        
    if room_settings_available:
        return "ROOM_SETTINGS"
    else:
        send_welcome_form(room_id, person_settings)
        
def act_save_room_settings(room_id, event_name, settings, args_dict):
    """save the settings provided by Room settings card
    
    arguments:
    room_id -- room id to which the settings is related
    event_name -- name of the events
    settings -- current active settings (user- or space-level)
    args_dict -- arguments passed to the event handler function
    """
    inputs = args_dict.get("inputs", {})
    room_settings = BotSettings(db = ddb, settings_id = room_id)
    room_settings.settings = inputs
    flask_app.logger.debug("saving room settings, db: {}, id: {}, data: {}".format(room_settings._db, room_settings._settings_id, room_settings.settings))
    room_settings.save()
    
    send_welcome_form(room_id, room_settings)
        
def act_save_user_settings(room_id, event_name, settings, args_dict):
    """save the settings provided by User settings card in 1-1 communication with a user
    
    arguments:
    room_id -- room id to which the settings is related
    event_name -- name of the events
    settings -- current active settings (user- or space-level)
    args_dict -- arguments passed to the event handler function
    """
    person_id = args_dict.get("personId")
    inputs = args_dict.get("inputs", {})
    person_settings = BotSettings(db = ddb, settings_id = person_id)
    person_settings.settings = inputs
    person_settings.settings = {"user_updated": True}
    flask_app.logger.debug("saving user settings, db: {}, id: {}, person id: {}, data: {}".format(person_settings._db, person_settings._settings_id, person_id, person_settings.settings))
    person_settings.save()

def send_welcome_form(room_id, settings):
    """send the Welcome form to the Space
    
    arguments:
    room_id -- room id to which the settings is related
    settings -- current active settings (user- or space-level)
    """
    attach = [bc.wrap_form(bc.localize(bc.WELCOME_TEMPLATE, settings.settings["language"]))]
    form_type = "WELCOME_FORM"
    send_message({"roomId": room_id}, "welcome form", attachments=attach, form_type=form_type)
    
def act_removed_from_space(room_id, event_name, settings, args_dict):
    """handle the Bot-removed-from-a-space event
    
    arguments:
    room_id -- room id to which the settings is related
    event_name -- name of the events
    settings -- current active settings (user- or space-level)
    args_dict -- arguments passed to the event handler function
    """
    """Bot was removed from the Space"""
    flask_app.logger.debug("removed from space {}".format(room_id))

def act_start_end_meeting(room_id, event_name, settings, args_dict):
    """handle the Meeting start event
    
    arguments:
    room_id -- room id to which the settings is related
    event_name -- name of the events
    settings -- current active settings (user- or space-level)
    args_dict -- arguments passed to the event handler function
    """
    """Meeting started/ended - sent the proper card"""
    try:
        flask_app.logger.debug("{} meeting args: {}".format(event_name, args_dict))
        
        # TODO remove previous start/end meeting form
        
        moderators = get_moderators(room_id)
                
        # only moderators (if there are any) are allowed to start/end meeting
        if moderators:
            if person_id not in moderators:
                flask_app.logger.debug("{} is not a moderator in the roomId {}, ignorng start/end request".format(person_id, room_id))
                room_details = webex_api.rooms.get(room_id)
                room_name = room_details.title
                action_name = bc.localize("{{loc_act_start_end_meeting_1}}", settings.settings["language"])
                next_state = "MEETING_ACTIVE"
                if event_name == "ev_start_meeting":
                    action_name = bc.localize("{{loc_act_start_end_meeting_2}}", settings.settings["language"])
                    next_state = "MEETING_INACTIVE"
                send_message({"toPersonId": person_id}, bc.localize("{{loc_act_start_end_meeting_3}}", settings.settings["language"]).format(room_name, action_name))
                
                return next_state
        
        inputs = args_dict.get("inputs", {})

        meeting_info = {
            "subject": inputs.get("meeting_subject", "")
        }
        
        timestamp = create_timestamp()
        if event_name == "ev_start_meeting":
            template = bc.localize(bc.START_MEETING_TEMPLATE, settings.settings["language"])
            form_type = "START_MEETING_FORM"
            meeting_status = "MEETING_START"
        else:
            template = bc.localize(bc.END_MEETING_TEMPLATE, settings.settings["language"])
            form_type = "END_MEETING_FORM"
            meeting_status = "MEETING_END"
            
            clear_meeting_presence(room_id)
        
        flask_app.logger.debug("Saving meeting \"{}\"status {}, timestamp {}".format(meeting_info["subject"], meeting_status, timestamp))
        ddb.save_db_record(room_id, timestamp, meeting_status, **meeting_info)
            
        user_info = webex_api.people.get(args_dict["personId"])
        form = bc.nested_replace(template, "display_name", user_info.displayName)
        form = bc.nested_replace(form, "meeting_subject", meeting_info["subject"])
        attach = [bc.wrap_form(bc.localize(form, settings.settings["language"]))]
        msg_id = send_message({"roomId": room_id}, "{} meeting form".format(event_name), attachments=attach, form_type=form_type)
        
        # send meeting summary in XLSX format
        if event_name == "ev_end_meeting":
            results_items, meeting_name = get_last_meeting_results(room_id)
            if len(results_items) > 0:
                my_url = get_my_url()
                if my_url:
                    now = datetime.now()
                    file_name = now.strftime("%Y_%m_%d_%H_%M_")

                    complete_results, header_list = create_results(results_items, settings)
                    xls_stream = create_xls_stream(complete_results, header_list)
                    
                    msg_data = {
                        "roomId": room_id,
                        "parentId": msg_id,
                        "markdown": bc.localize("{{loc_act_start_end_meeting_4}}", settings.settings["language"])
                    }
                    
                    send_file_stream(msg_data, file_name + meeting_name + ".xlsx", XLSX_CONTENT_TYPE, xls_stream)
    
    except ApiError as e:
        flask_app.logger.error("{} meeting form create failed: {}.".format(event_name, e))
        
def get_moderators(room_id):
    """return a list of Space moderators
    
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

def act_start_poll(room_id, event_name, settings, args_dict):
    """handle the start poll event
    
    arguments:
    room_id -- room id to which the settings is related
    event_name -- name of the events
    settings -- current active settings (user- or space-level)
    args_dict -- arguments passed to the event handler function
    """
    """start the poll, send the poll card"""
    inputs = args_dict.get("inputs", {})
    subject = inputs.get("poll_subject")
    time_limit = inputs.get("time_limit")
    form_type = "POLL_FORM"
    try:
        user_info = webex_api.people.get(args_dict["personId"])
        form = bc.nested_replace(bc.POLL_TEMPLATE, "display_name", user_info.displayName)
        form = bc.nested_replace(form, "poll_subject", subject)
        form = bc.nested_replace(form, "time_limit", time_limit)
        attach = [bc.wrap_form(bc.localize(form, settings.settings["language"]))]
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
        
def act_end_poll(room_id, event_name, settings, args_dict):
    """end poll both automatically and manually"""
    flask_app.logger.debug("end poll args: {}".format(args_dict))
    # init_globals() # make sure ddb is available
    
    poll_state, inputs = get_last_poll_state(room_id)
    subject = inputs.get("poll_subject")
    time_limit = inputs.get("time_limit")
    form_id = inputs.get("form_id")
    args_id = args_dict.get("form_id", None)
    if args_id and args_id != form_id:
        flask_app.logger.info("running form id and ending form id do not match, no action {} != {}". format(args_id, form_id))
        return "POLL_RUNNING" # keep the poll running
        
    if poll_state == "RUNNING":
        flask_app.logger.debug("deleting poll \"{}\" form {}".format(subject, form_id))
        try:
            webex_api.messages.delete(form_id)

            publish_poll_results(room_id, form_id, subject, settings, time_limit=time_limit)

        except ApiError as e:
            flask_app.logger.error("message {} delete failed: {}.".format(form_id, e))
        
        save_last_poll_state(room_id, "ENDED", args_dict)
    else:
        flask_app.logger.debug("poll \"{}\" - {} not running (state: {})".format(subject, form_id, poll_state))
        
def publish_poll_results(room_id, form_id, subject, settings, time_limit=bc.DEFAULT_TIME_LIMIT):
    """send card with poll results, save results to the database"""
    flask_app.logger.debug("publishing poll \"{}\" results, form id: {}".format(subject, form_id))
    poll_results = ddb.query_db_record(form_id, "POLL_DATA")
    yea_res = []
    nay_res = []
    abstain_res = []
    active_users = []
    vote_results = []
    name_key = bc.localize("{{loc_publish_poll_results_1}}", settings.settings["language"])
    choice_key = bc.localize("{{loc_publish_poll_results_6}}", settings.settings["language"])
    for res in poll_results:
        vote = res.get("vote")
        voter_id = res["sk"]
        active_users.append(voter_id)
        voter_data = webex_api.people.get(voter_id)
        if vote == "yea":
            yea_res.append(voter_data.displayName)
            vote_results.append({name_key: voter_data.displayName, choice_key: bc.localize("{{loc_publish_poll_results_2}}", settings.settings["language"])})
        elif vote == "nay":
            nay_res.append(voter_data.displayName)
            vote_results.append({name_key: voter_data.displayName, choice_key: bc.localize("{{loc_publish_poll_results_3}}", settings.settings["language"])})
        elif vote == "abstain":
            abstain_res.append(voter_data.displayName)
            vote_results.append({name_key: voter_data.displayName, choice_key: bc.localize("{{loc_publish_poll_results_4}}", settings.settings["language"])})
            
    present_users = get_present_users(room_id)
    passive_users = list(set(present_users).difference(set(active_users)))
    for user_id in passive_users:
        voter_data = webex_api.people.get(user_id)
        abstain_res.append(voter_data.displayName)
        vote_results.append({name_key: voter_data.displayName, choice_key: bc.localize("{{loc_publish_poll_results_4}}", settings.settings["language"])})
        
    voter_columns = {
        "type": "ColumnSet",
        "columns": []
    }

    voter_columns["columns"].append(create_result_column(yea_res, style=bc.YEA_STYLE))
    voter_columns["columns"].append(create_result_column(nay_res, style=bc.NAY_STYLE))
    voter_columns["columns"].append(create_result_column(abstain_res, style=bc.ABSTAIN_STYLE))
    vote_results.sort(key=lambda x: x[name_key].split(" ")[-1])
    
    rslt = {
        "vote_results": vote_results,
        "subject": subject,
        "timestamp": create_timestamp()
    }
    ddb.save_db_record(room_id, form_id, "RESULTS", **rslt)
        
    poll_result_attachment = bc.nested_replace(bc.POLL_RESULTS_TEMPLATE, "poll_subject", subject)
    poll_result_attachment = bc.nested_replace(poll_result_attachment, "yea_count", len(yea_res))
    poll_result_attachment = bc.nested_replace(poll_result_attachment, "nay_count", len(nay_res))
    poll_result_attachment = bc.nested_replace(poll_result_attachment, "abstain_count", len(abstain_res))
    poll_result_attachment["body"].append(voter_columns)
    poll_block = bc.nested_replace(bc.NEXT_POLL_BLOCK, "time_limit", time_limit)
    poll_result_attachment["body"].append(poll_block)
    poll_result_attachment["body"].append(bc.END_MEETING_BLOCK)
    
    msg_id = send_message({"roomId": room_id}, "{} poll results".format(subject), attachments=[bc.wrap_form(bc.localize(poll_result_attachment, settings.settings["language"]))], form_type="POLL_RESULTS")
    
    # publish results after each poll?
    if settings.settings["partial_results"] and len(vote_results) > 0:
        my_url = get_my_url()
        if my_url:
            result_name = unidecode(subject).lower().replace(" ", "_")
            now = datetime.now()
            file_name = now.strftime("%Y_%m_%d_%H_%M_") + result_name
            
            complete_results, header_list = create_partial_results(vote_results, settings)
            xls_stream = create_xls_stream(complete_results, header_list)

            msg_data = {
                "roomId": room_id,
                "parentId": msg_id,
                "markdown": bc.localize("{{loc_publish_poll_results_5}}", settings.settings["language"])
            }
            
            send_file_stream(msg_data, file_name + ".xlsx", XLSX_CONTENT_TYPE, xls_stream)
    
def create_result_column(result, style = "default"):
    """create an individual result column for the card"""
    result.sort(key=lambda x: x.split(" ")[-1]) # sort by last name
    column = []
    for res in result:
        column.append(bc.nested_replace(bc.RESULT_PARTICIPANT_TEMPLATE, "display_name", res))
        
    column_result = {
        "type": "Column",
        "width": "stretch",
        "style": style,
        "items": column
    }
                
    flask_app.logger.debug("result column: {}".format(column_result))
        
    return column_result
    
def act_presence(room_id, event_name, settings, args_dict):
    """presence indication"""
    message_id = args_dict.get("messageId")
    person_id = args_dict.get("personId")
    set_presence(room_id, person_id, True)
    
def set_presence(room_id, person_id, status):
    """save user's presence in the Space id (room_id)"""
    status_data = {"status": status}
    ddb.save_db_record(room_id, person_id, "PRESENT", **status_data)
    flask_app.logger.debug("Presence status for user {} set to {}, roomId: {}".format(person_id, status, room_id))    
        
def act_poll_data(room_id, event_name, settings, args_dict):
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
["ROOM_SETTINGS", "ev_room_settings_data", act_save_room_settings, "WELCOME"],
["MEETING_INACTIVE", "ev_room_settings_data", act_save_room_settings, "same_state"],
["MEETING_INACTIVE", "ev_start_meeting", act_start_end_meeting, "MEETING_ACTIVE"],
["MEETING_ACTIVE", "ev_presence", act_presence, "same_state"],
["POLL_RUNNING", "ev_presence", act_presence, "same_state"],
["any_state", "ev_end_meeting", act_start_end_meeting, "MEETING_INACTIVE"],
# ["any_state", "ev_start_poll", act_start_poll, "POLL_RUNNING"],
["MEETING_ACTIVE", "ev_start_poll", act_start_poll, "POLL_RUNNING"],
["POLL_RUNNING", "ev_poll_data", act_poll_data, "same_state"],
["POLL_RUNNING", "ev_end_poll", act_end_poll, "MEETING_ACTIVE"],
["any_state", "ev_removed_from_space", act_removed_from_space, "REMOVED"],
["any_state", "ev_user_settings_data", act_save_user_settings, "same_state"]
]

def create_timestamp():
    """time stamp in UTC (ISO 8601) format - used as secondary key in some DB operations"""
    return datetime.utcnow().isoformat()[:-3]+'Z'
    
def parse_timestamp(time_str):
    """create datetime object from UTC (ISO 8601) string"""
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))

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
                    webex_api.webhooks.create(name="Webhook for event \"{}\" on resource \"{}\"".format(event, resource), targetUrl=target_url, resource=resource, event=event)
                status = True
                flask_app.logger.debug("Webhook for {}/{} was successfully created".format(resource, event))
            except ApiError as e:
                flask_app.logger.error("Webhook create failed: {}.".format(e))
            
    return status

def greetings(personal=True):
    
    greeting_msg = bc.localize("{{loc_1_1_welcome_1}}", "en_US")

    return greeting_msg

def help_me(personal=True):

    greeting_msg = """
Dummy help.
"""

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
            save_form_info(get_bot_id(), res_msg.id, form_type, form_params) # sender is the owner
        else:
            flask_app.logger.debug("Not saving, attach len: {}, form type: {}".format(len(attachments), form_type))
            
        return res_msg.id
    except ApiError as e:
        flask_app.logger.error("Message create failed: {}.".format(e))
        
def send_file_stream(msg_data, file_name, content_type, file_stream):
    try:
        flask_app.logger.debug("Send file {} with data: {}".format(file_name, msg_data))
        
        msg_data["files"] = (file_name, file_stream, content_type)
        
        multipart_data = MultipartEncoder(msg_data)
        headers = {'Content-type': multipart_data.content_type}
        
        json_data = webex_api.messages._session.post('messages', data=multipart_data, headers=headers)
        res_msg = webex_api.messages._object_factory('message', json_data)
        flask_app.logger.debug("Message with file created: {}".format(dict(res_msg.json_data)))
        
        return res_msg.id
    except ApiError as e:
        flask_app.logger.error("Message create failed: {}.".format(e))
        
def get_bot_id():
    bot_id = os.getenv("BOT_ID", None)
    if bot_id is None:
        me = get_bot_info()
        bot_id = me.id
        
    # flask_app.logger.debug("Bot id: {}".format(bot_id))
    return bot_id
    
def get_bot_info():
    try:
        me = webex_api.people.me()
        if me.avatar is None:
            me.avatar = DEFAULT_AVATAR_URL
            
        # flask_app.logger.debug("Bot info: {}".format(me))
        
        return me
    except ApiError as e:
        flask_app.logger.error("Get bot info error, code: {}, {}".format(e.status_code, e.message))
        
def get_bot_name():
    me = get_bot_info()
    return me.displayName
        
def init_globals():
    global ddb

    ddb = DDB_Single_Table()
    flask_app.logger.debug("initialize DDB object {}".format(ddb))

# Flask part of the code

"""
1. initialize database table if needed
2. start event checking thread
"""
@flask_app.before_first_request
def before_first_request():
    me = get_bot_info()
    email = me.emails[0]

    if ("@sparkbot.io" not in email) and ("@webex.bot" not in email):
        flask_app.logger.error("""
You have provided access token which does not belong to a bot ({}).
Please review it and make sure it belongs to your bot account.
Do not worry if you have lost the access token.
You can always go to https://developer.ciscospark.com/apps.html 
URL and generate a new access token.""".format(email))

    init_globals()
    
@flask_app.before_request
def before_request():
    init_globals()
    
"""
Main function which handles the webhook events. It reacts both on messages and button&card events

Look at the 'msg +=' for workflow explanation
"""

# @task
def handle_webhook_event(webhook):
    action_list = []
    bot_info = get_bot_info()
    bot_email = bot_info.emails[0]
    bot_name = bot_info.displayName
    if webhook["data"].get("personEmail") != bot_email:
        flask_app.logger.info(json.dumps(webhook))
        
    msg = ""
    attach = []
    target_dict = {"roomId": webhook["data"]["roomId"]}
    form_type = None
    out_messages = [] # additional messages apart of the standard response
        
# handle Bot's membership events (Bot added/removed from Space or 1-1 communication)
    if webhook["resource"] == "memberships":
        if webhook["data"]["personId"] == get_bot_id():
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
                    fsm_handle_event(webhook["data"]["roomId"], "ev_added_to_space", webhook)
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
    button_pressed = inputs.get("action", None)
    if form_type in ["WELCOME_FORM", "END_MEETING_FORM"]:
        if button_pressed == "start_meeting":
            event = "ev_start_meeting"
        elif button_pressed == "change_settings":
            event = "ev_room_settings_data"
    elif form_type in ["START_MEETING_FORM", "POLL_RESULTS"]:
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
    elif form_type == "ROOM_SETTINGS_FORM":
        event = "ev_room_settings_data"
    elif form_type == "USER_SETTINGS_FORM":
        event = "ev_user_settings_data"
        
    return event
    
"""
Bot setup. Used mainly for webhook creation and gathering a dynamic Bot URL.
"""

@flask_app.route("/", methods=["GET", "POST"])
def spark_webhook():
    if request.method == "POST":
        webhook = request.get_json(silent=True)
        flask_app.logger.debug("Webhook received: {}".format(webhook))
        handle_webhook_event(webhook)        
    elif request.method == "GET":
        bot_info = get_bot_info()
        message = "<center><img src=\"{0}\" alt=\"{1}\" style=\"width:256; height:256;\"</center>" \
                  "<center><h2><b>Congratulations! Your <i style=\"color:#ff8000;\">{1}</i> bot is up and running.</b></h2></center>".format(bot_info.avatar, bot_info.displayName)
                  
        message += "<center><b>I'm hosted at: <a href=\"{0}\">{0}</a></center>".format(request.url)
        res = create_webhook(request.url)
        if res is True:
            message += "<center><b>New webhook created sucessfully</center>"
        else:
            message += "<center><b>Tried to create a new webhook but failed, see application log for details.</center>"

        return message
        
    flask_app.logger.debug("Webhook handling done.")
    return "OK"
        
def create_partial_results(results_items, settings):
    user_list = []
    name_key = bc.localize("{{loc_publish_poll_results_1}}", settings.settings["language"])
    choice_key = bc.localize("{{loc_publish_poll_results_6}}", settings.settings["language"])
    for poll_res in results_items:
        user_list.append(poll_res.get(name_key, ""))
        
    user_list = list(set(user_list)) # get unique names
    user_list.sort(key=lambda x: x.split(" ")[-1]) # sort by last name
    flask_app.logger.debug("got user list: {}".format(user_list))
    
    header_list = [name_key, choice_key]
    complete_results = []
    for user in user_list:
        user_vote_list = [user]
        for poll_res in results_items:
            if poll_res[name_key] == user:
                user_vote_list.append(poll_res[choice_key])
            
        complete_results.append(user_vote_list)
        
    flask_app.logger.debug("Create partial results: {}".format(complete_results))
        
    return complete_results, header_list

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
            
def get_name_from_results(vote_results, name_key):
    name_list = []
    for vote in vote_results:
        name = vote.get(name_key)
        if name:
            name_list.append(name)
            
    return name_list
    
def create_results(results_items, settings):
    name_key = bc.localize("{{loc_publish_poll_results_1}}", settings.settings["language"])
    choice_key = bc.localize("{{loc_publish_poll_results_6}}", settings.settings["language"])

    results_items.sort(key=lambda x: x["timestamp"])
        
    user_list = []
    subject_list = []
    for poll_res in results_items:
        vote_results = poll_res.get("vote_results", [])
        user_list += get_name_from_results(vote_results, name_key)
        subject_list.append(poll_res["subject"])
        
    user_list = list(set(user_list)) # get unique names
    user_list.sort(key=lambda x: x.split(" ")[-1]) # sort by last name
    flask_app.logger.debug("got user list: {}".format(user_list))
    
    header_list = [name_key] + subject_list
    complete_results = []
    for user in user_list:
        user_vote_list = [user]
        for poll_res in results_items:
            vote_results = poll_res.get("vote_results", [])
            user_vote_list.append(get_vote_for_user(vote_results, user, name_key, choice_key))
            
        complete_results.append(user_vote_list)
        
    return complete_results, header_list
    
def create_xls_stream(complete_results, header_list):
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
    
    return bi
    
def get_vote_for_user(vote_results, user, name_key, choice_key):
    for vote_item in vote_results:
        if vote_item[name_key] == user:
            return vote_item[choice_key]
            
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
