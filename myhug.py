import hug
import os
import requests
import json
import re
from datetime import datetime
from botFunctions import TEST_EMAIL, TEST_NAME, EVENT_SMARTSHEET_ID, AREA_COLUMN_FILTER, NO_COLUMN_FILTER
from botFunctions import EVENTS_EMAIL, EVENTS_NAME
from botFunctions import CODE_PRINT_COLUMNS, EMAIL_COLUMNS
from botFunctions import ss_get_client, get_all_areas_and_associated_states
from botFunctions import format_help_msg,get_all_data_and_filter, format_code_print_for_bot
from botFunctions import generate_html_table_for_bot, map_cell_data_to_columnId
from botFunctions import generate_email, bot_send_email, send_log_to_ss



URL = "https://api.ciscospark.com/v1/messages"
TEST_HEADERS = {
    'Authorization': os.environ['BOT_TOKEN'],
    'Content-Type': "application/json",
    'cache-control': "no-cache"
}
EVENTS_HEADERS = {
    'Authorization': os.environ['EVENTS_TOKEN'],
    'Content-Type': "application/json",
    'cache-control': "no-cache"
}


@hug.post('/hello', examples='hello')
def hello(body):
    """
        Test bot for new features.
    """
    #print("GOT {}: {}".format(type(body), repr(body)))
    room_id = body["data"]["roomId"]
    identity = body["data"]["personEmail"]
    text = body["data"]["id"]
    print("see POST from {}".format(identity))
    if identity != TEST_EMAIL:
        print("{}-----{}".format(identity,TEST_EMAIL))
        #command = get_msg_sent_to_bot(text).lower()
        command = get_msg_sent_to_bot(text, TEST_HEADERS)
        command = (command.replace(TEST_NAME, '')).strip()
        command = (command.replace('@', '')).strip()
        print("stripped command: {}".format(command))
        process_bot_input_command(room_id,command, TEST_HEADERS, TEST_NAME)
        send_log_to_ss(TEST_NAME,str(datetime.now()),identity,command,room_id)


@hug.post('/events', examples='events')
def events(body):
    """
        Production for EVENTS-TBD bot
        Takes the webhook data <body> and parses out the sender and the message
        Must filter out all messages sent by bot as those come back as part of webhook
        Strips the command of the botname, and then sends the command to take action
        Finally, we log the interaction in smartsheets

        Future: regex search identity for domain verification
    """
    #print("GOT {}: {}".format(type(body), repr(body)))
    room_id = body["data"]["roomId"]
    identity = body["data"]["personEmail"]
    text = body["data"]["id"]
    print("see POST from {}".format(identity))
    if identity != EVENTS_EMAIL:
        print("{}-----{}".format(identity,EVENTS_EMAIL))
        #command = get_msg_sent_to_bot(text).lower()
        command = get_msg_sent_to_bot(text, EVENTS_HEADERS)
        command = (command.replace(EVENTS_NAME, '')).strip()
        command = (command.replace('EVENT-TBD', '')).strip() #temp due to typo
        command = (command.replace('@', '')).strip()
        print("stripped command: {}".format(command))
        process_bot_input_command(room_id,command, EVENTS_HEADERS, EVENTS_NAME)
        send_log_to_ss(EVENTS_NAME,str(datetime.now()),identity,command,room_id)



def process_bot_input_command(room_id,command, headers, bot_name):
    """ 
        Take the 1st word sent to the bot: check if it is a command
        If command, process, else, send help message
        If events trigger:
            sanitize the command, remove commas, spaces, and bytestrings
            if 2 digit state code, capitalize it
            Fetch the data from smartsheets, then search based on input
            Format the data and send to teams room
    """
    ss_client = ss_get_client(os.environ['SMARTSHEET_TOKEN'])
    trigger = command.split(' ')
    if trigger[0] in ("events",'Events','EVENTS','Event','event','EVENT'):
        state_list_joined = command.replace(trigger[0],'').strip()
        print("command edit 1: {}".format(state_list_joined))
        state_list_joined = state_list_joined.replace('\xa0','')
        print("command edit 2: {}".format(state_list_joined))        
        state_list_joined = state_list_joined.replace(',',' ')
        print("command edit 3: {}".format(state_list_joined))
        #re.sub('\s+', ' ', mystring).strip() #remove additional whitespace - also a way with re to strip non alpha characters
        state_list = state_list_joined.split(' ')
        print("state list: {}".format(str(state_list)))
        for state in range(len(state_list)):
            if len(state_list[state]) == 2:
                state_list[state] = state_list[state].upper()
        print("Final state list: {}".format(str(state_list)))
        data = get_all_data_and_filter(ss_client,EVENT_SMARTSHEET_ID, state_list,NO_COLUMN_FILTER)
        msg = format_code_print_for_bot(data,state_list_joined,CODE_PRINT_COLUMNS)
        response = bot_post_to_room(room_id, msg, headers)
        msg = generate_html_table_for_bot(data,state_list_joined,EMAIL_COLUMNS)
        email_filename = generate_email(msg)
        response = bot_send_email(room_id,email_filename)        
    else:
        area_dict = get_all_areas_and_associated_states(ss_client,EVENT_SMARTSHEET_ID,AREA_COLUMN_FILTER)
        msg = format_help_msg(area_dict, bot_name)
        response = bot_post_to_room(room_id, msg, headers)
                    


def get_msg_sent_to_bot(msg_id, headers):
    urltext = URL + "/" + msg_id
    payload = ""

    response = requests.request("GET", urltext, data=payload, headers=headers)
    response = json.loads(response.text)
    #print ("Message to bot : {}".format(response["text"]))
    return response["text"]


def bot_post_to_room(room_id, message, headers):
    #try to post
    payload = {"roomId": room_id,"markdown": message}
    response = requests.request("POST", URL, data=json.dumps(payload), headers=headers)
    #error handling
    if response.status_code != 200:
        #modify function to receive user_input as well so we can pass through
        user_input = "some test message for the moment"
        #send to the DEVs bot room
        error_handling(response,response.status_code,user_input,room_id,headers)


      


def error_handling(response,err_code,user_input,room_id,headers):
    """
        Random description to be filled out later
        Just testing branch git control
        Conflicting statement - master branch
    """
    error = json.loads(response.text) #converts to type DICT
    #grabs the error response from teams
    #Example: {"message":"Unable to post message to room: \"The request payload is too big\"",
    #"errors":[{"description":"Unable to post message to room: \"The request payload is too big\""}],
    # "trackingId":"ROUTER_5C5510D1-D8A4-01BB-0055-48A302E70055"}

    #send to DEVs bot room
    message = ("**Error code**: {}  \n**User input**: {}  \n**Error**: {}".format(err_code,user_input,error["message"]))
    bot_post_to_room(os.environ['TEST_ROOM_ID'],message,headers)
    
    #need to add error handling here
    #if XYZ in response.text then, etc
    search_obj = re.search(r'7439',error["message"])
    if search_obj:
        message = "Too many results for Teams output, sending email instead:"
    else:
        message = "Looks like we've hit a snag! Sending feedback to the development team."
    bot_post_to_room(room_id,message,headers)

