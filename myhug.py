import hug
import os
import requests
import json
from botFunctions import BOT_EMAIL, BOT_NAME, EVENT_SMARTSHEET_ID, AREA_COLUMN_FILTER, NO_COLUMN_FILTER
from botFunctions import ss_get_client, get_all_areas_and_associated_states
from botFunctions import format_help_msg,get_all_data_and_filter, format_code_print_for_bot
from botFunctions import generate_html_table_for_bot, map_cell_data_to_columnId
from botFunctions import generate_email, bot_send_email



url = "https://api.ciscospark.com/v1/messages"
headers = {
    'Authorization': os.environ['BOT_TOKEN'],
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
    if identity != BOT_EMAIL:
        command = get_msg_sent_to_bot(text).lower()
        command = (command.replace(bot_name, '')).strip()
        print("stripped command: {}".format(command))
        process_bot_input_command(command)



def process_bot_input_command(room_id,command):
    """ """
    ss_client == ss_get_client(os.environ['SMARTSHEET_TOKEN'])
    if command in ("events",'Events','EVENTS','Event','event','EVENT'):
        state_list_joined = command.replace('events','').strip()
        state_list = state_list_joined.split(' ')

        data = get_all_data_and_filter(ss_client,EVENT_SMARTSHEET_ID, state_list,NO_COLUMN_FILTER)
        msg = format_code_print_for_bot(BOT_NAME,data,state_list_joined)
        response = bot_post_to_room(room_id, msg)
        msg = generate_html_table_for_bot(data,state_list_joined)
        #msg = test_generate_html_table_v3(ss_client,EVENT_SMARTSHEET_ID,'CA')
        email_filename = generate_email(msg)
        response = bot_send_email(room_id,email_filename)        
    else:
        area_dict = get_all_areas_and_associated_states(ss_client,EVENT_SMARTSHEET_ID,AREA_COLUMN_FILTER)
        msg = format_help_msg(area_dict)
        response = bot_post_to_room(room_id, msg)
                    


def bot_post_to_room(room_id, message):

    payload = {"roomId": room_id,"markdown": message}
    response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
    response = json.loads(response.text)
    #print("botpost response: {}".format(response)) 
    return response["text"]

def get_msg_sent_to_bot(msg_id):
    urltext = url + "/" + msg_id
    payload = ""

    response = requests.request("GET", urltext, data=payload, headers=headers)
    response = json.loads(response.text)
    #print ("Message to bot : {}".format(response["text"]))
    return response["text"]



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
