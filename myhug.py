import hug
import os
import requests
import json
from botFunctions import TEST_EMAIL, TEST_NAME, EVENT_SMARTSHEET_ID, AREA_COLUMN_FILTER, NO_COLUMN_FILTER
from botFunctions import EVENTS_EMAIL, EVENTS_NAME
from botFunctions import CODE_PRINT_COLUMNS, EMAIL_COLUMNS
from botFunctions import ss_get_client, get_all_areas_and_associated_states
from botFunctions import format_help_msg,get_all_data_and_filter, format_code_print_for_bot
from botFunctions import generate_html_table_for_bot, map_cell_data_to_columnId
from botFunctions import generate_email, bot_send_email



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
    """Test for webex teams"""
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


@hug.post('/events', examples='events')
def events(body):
    """Test for webex teams"""
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
        command = (command.replace('@', '')).strip()
        print("stripped command: {}".format(command))
        process_bot_input_command(room_id,command, EVENTS_HEADERS, EVENTS_NAME)



def process_bot_input_command(room_id,command, headers, bot_name):
    """ """
    ss_client = ss_get_client(os.environ['SMARTSHEET_TOKEN'])
    trigger = command.split(' ')
    if trigger[0] in ("events",'Events','EVENTS','Event','event','EVENT'):
        state_list_joined = command.replace(trigger[0],'').strip()
        print("command edit 1: {}".format(state_list_joined))
        state_list_joined = state_list_joined.replace('\xa0','')
        print("command edit 2: {}".format(state_list_joined))        
        state_list_joined = state_list_joined.replace(',',' ')
        print("command edit 3: {}".format(state_list_joined))
      
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
                    

'''
def bot_post_to_room(room_id, message, headers):

    payload = {"roomId": room_id,"markdown": message}
    response = requests.request("POST", URL, data=json.dumps(payload), headers=headers)
    response = json.loads(response.text)
    #print("botpost response: {}".format(response)) 
    return response["text"]
'''

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
    message = "Looks like we've hit a snag! Sending feedback to the development team."
    bot_post_to_room(room_id,message,headers)


#goal would be to say <botname> <state code>
    #city is too narrow a field, area too broad

#def get all areas and associated states
    #pull area column of event sheet, and do set list (or just type manually as not that many)
    #create a dict with [] keys:
        #temp_dict = {"south":[],"west":[]}
    #column_ids=[<area id>,<city id>]
    #sheet = smartsheet.Sheets.get_sheet(sheet_id, column_ids=column_ids)
    #for row in sheet.row:
        #temp_dict[row.cells[0]].append(row.cells[1])
    #area_dict = {}
    #for key, value in temp_dict:
        #area_dict[key] = set(value)
    #return area_dict
        #should look like: {"south":["TX","AR","NC",etc],"west":["CA","OR",etc]}

#def botprint all areas and associated states(area_dict)
    #would be the default message when no state is detected
    #msg = ""
    #msg += "any static info such as a reminder to add events to smartsheet link"
    #for key, value in area_dict:
        #msg += "**{}**  \n".format(key)  #bolded area name
        #msg += "```  \n {}  \n```".format(value.join(' '))  #join all states in list and separate with space
