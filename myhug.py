import hug
import os
import requests
import json
import re
from datetime import datetime
from operator import itemgetter
from botFunctions import TEST_EMAIL, TEST_NAME, EVENT_SMARTSHEET_ID, AREA_COLUMN_FILTER, NO_COLUMN_FILTER
from botFunctions import EVENTS_EMAIL, EVENTS_NAME
from botFunctions import CODE_PRINT_COLUMNS, EMAIL_COLUMNS,CODE_PRINT_COLUMNS_MOBILE
from botFunctions import ss_get_client, get_all_areas_and_associated_states
from botFunctions import format_help_msg,get_all_data_and_filter, format_code_print_for_bot, format_code_print_for_bot_mobile
from botFunctions import generate_html_table_for_bot, map_cell_data_to_columnId
from botFunctions import generate_email, bot_send_email, send_log_to_ss
from botFunctions import command_parse, sanitize_commands, process_state_codes, process_arch_filter, filter_data_by_architecture




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

TEST_PERSON_URL = "https://api.ciscospark.com/v1/people"
TEST_CARD_MSG_URL = "https://api.ciscospark.com/v1/attachment/actions"

'''
CARDS example
{
  "id": "Y2lzY29zcGFyazovL3VzL1dFQkhPT0svOTZhYmMyYWEtM2RjYy0xMWU1LWExNTItZmUzNDgxOWNkYzlh",
  "name": "My Attachment Action Webhook",
  "resource": "attachmentActions",
  "event": "created",
  "orgId": "OTZhYmMyYWEtM2RjYy0xMWU1LWExNTItZmUzNDgxOWNkYzlh",
  "appId": "Y2lzY29zcGFyazovL3VzL0FQUExJQ0FUSU9OL0MyNzljYjMwYzAyOTE4MGJiNGJkYWViYjA2MWI3OTY1Y2RhMzliNjAyOTdjODUwM2YyNjZhYmY2NmM5OTllYzFm",
  "ownedBy": "creator",
  "status": "active",
  "actorId": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS83MTZlOWQxYy1jYTQ0LTRmZ",
  "data": {
    "id": "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi85NmFiYzJhYS0zZGNjLTE",
    "type": "submit",
    "messageId": "GFyazovL3VzL1BFT1BMRS80MDNlZmUwNy02Yzc3LTQyY2UtOWI4NC",
    "personId": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS83MTZlOWQxYy1jYTQ0LTRmZ",
    "roomId": "L3VzL1BFT1BMRS80MDNlZmUwNy02Yzc3LTQyY2UtOWI",
    "created": "2016-05-10T19:41:00.100Z"
  }
}
'''

'''
Get card attachment
{
  "type": "submit",
  "messageId": "GFyazovL3VzL1BFT1BMRS80MDNlZmUwNy02Yzc3LTQyY2UtOWI4NC",
  "inputs": {
    "Name": "John Andersen",
    "Url": "https://example.com",
    "Email": "john.andersen@example.com",
    "Tel": "+1 408 526 7209"
  },
  "id": "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi85NmFiYzJhYS0zZGNjLTE",
  "personId": "Y2lzY29zcGFyazovL3VzL1BFT1BMRS83MTZlOWQxYy1jYTQ0LTRmZ",
  "roomId": "L3VzL1BFT1BMRS80MDNlZmUwNy02Yzc3LTQyY2UtOWI",
  "created": "2016-05-10T19:41:00.100Z"
}
'''

@hug.post('/hello', examples='hello')
def hello(body):
    """
        Test bot for new features.
    """
    #print(f"GOT {type(body)}: {repr(body)}")
    resource = body["resource"]
    bot_event = body["event"]
    print(f'Resource = {resource}    Event = {bot_event}')
    if resource == "attachmentActions":
        card_id = body["id"]
        app_id = body["appId"]
        actor_id = body["actorId"]
        data_id = body["data"]["id"]
        person_id = body["data"]["personId"]
        room_id = body["data"]["roomId"]
        identity = test_get_person_from_id(person_id,TEST_HEADERS)
        card_inputs = test_get_card_msg(data_id,TEST_HEADERS)
        print(f"{card_inputs}")
        #test_create_card(room_id,TEST_HEADERS)

    elif resource == "messages":
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
            command = command.lower()  #added this, don't forget to move to events-bot as well
            print("stripped command: {}".format(command))
            process_bot_input_command(room_id,command, TEST_HEADERS, TEST_NAME)
            send_log_to_ss(TEST_NAME,str(datetime.now()),identity,command,room_id)
    elif resource == "memberships":
        room_id = body["data"]["roomId"]
        identity = body["data"]["personEmail"]
        print(f'made it to memberships identity={identity}')
        if bot_event == "created" and identity == TEST_EMAIL:
            test_create_card(room_id,TEST_HEADERS)


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
        command = command.lower()
        print("stripped command: {}".format(command))
        process_bot_input_command(room_id,command, EVENTS_HEADERS, EVENTS_NAME)
        send_log_to_ss(EVENTS_NAME,str(datetime.now()),identity,command,room_id)



def process_bot_input_command(room_id,command, headers, bot_name):
    """ 
        Provides a few different command options based in different lists. (commands should be lower case)
        Combines all lists together and checks if any keyword commands are detected...basically a manually created case/switch statement
        For each possible command, do something
        Is there an easier way to do this?
    """
    ss_client = ss_get_client(os.environ['SMARTSHEET_TOKEN'])
    state_filter = []
    arch_filter = []
    mobile_filter = False
    url_filter = False
    data = []
    
    command_list = [
        ("events",['event','events','-e']),
        ("mobile",['mobile','phone','-m']),
        ("filter",['filter','-f']),
        ("url_test",['url','-u'])
        #("command alias",["list of possible command entries"])
    ]
    result = command_parse(command_list,command)
    ##looks like: {"event":"TX FL AL","filter":"sec dc","mobile":""}
    if result:
        if "events" in result:
            print(f"made it to events:  {result['events']}") 
            state_filter = process_state_codes(result['events'].upper().split(" "),reverse=False)
        if "filter" in result:
            print(f"made it to filter:  {result['filter']}") 
            arch_filter = process_arch_filter(result['filter'])           
        if "mobile" in result:
            print(f"made it to mobile:  {result['mobile']}") 
            mobile_filter = True
        if "url_test" in result:
            print(f"made it to url_test:  {result['url_test']}") 
            url_filter = True

        data = get_all_data_and_filter(ss_client,EVENT_SMARTSHEET_ID, state_filter,arch_filter,url_filter,NO_COLUMN_FILTER)
        communicate_to_user(ss_client,room_id,headers,bot_name,data,state_filter,arch_filter,mobile_filter,url_filter,help=False)
    else:
        communicate_to_user(ss_client,room_id,headers,bot_name,data,state_filter,arch_filter,mobile_filter,url_filter,help=True)      

              
def get_msg_sent_to_bot(msg_id, headers):
    urltext = URL + "/" + msg_id
    payload = ""

    response = requests.request("GET", urltext, data=payload, headers=headers)
    response = json.loads(response.text)
    #print ("Message to bot : {}".format(response["text"]))
    return response["text"]

def test_get_person_from_id(person_id, headers):
    urltext = TEST_PERSON_URL + "/" + person_id
    payload = ""

    response = requests.request("GET", urltext, data=payload, headers=headers)
    response = json.loads(response.text)
    #print ("Message to bot : {}".format(response["emails"]))
    return response["emails"][0]


def test_get_card_msg(data_id, headers):
    urltext = TEST_CARD_MSG_URL + "/" + data_id
    payload = ""

    response = requests.request("GET", urltext, data=payload, headers=headers)
    response = json.loads(response.text)
    print ("Message to bot : {}".format(response))
    return response["inputs"]

def test_create_card(room_id,headers):
    card_payload = """
                           
    {
    "roomId": "Y2lzY29zcGFyazovL3VzL1JPT00vYTNjMjZkODAtMzZjYi0xMWU5LTk5NWItYjc2YjYzMTg0MjRj",
    "markdown": "[Tell us about yourself](https://www.example.com/form/book-vacation). We just need a few more details to get you booked for the trip of a lifetime!",
    "attachments": [
        {
        "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.0",
                    "body": [
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": 3,
                                    "items": [
                            {
                                "type": "TextBlock",
                                "text": "Events-tbd Bot",
                                "weight": "Bolder",
                                "size": "Medium"
                            },
                            {
                                "type": "TextBlock",
                                "text": "Enter a State Code from the list below:",
                                "isSubtle": true,
                                "wrap": true
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {
                                        "title": "South",
                                        "value": "TX FL CA"
                                    },
                                    {
                                        "title": "East",
                                        "value": "NC NY MA"
                                    }
                                ],
                                "id": "state_list"
                            },
                            {
                                "type": "TextBlock",
                                "text": "State Code",
                                "wrap": true
                            },
                            {
                                "type": "Input.Text",
                                "placeholder": "TX",
                                "id": "stace_code"
                            },
                            {
                                "type": "TextBlock",
                                "text": "Filter",
                                "wrap": true
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {
                                        "title": "Collaboration",
                                        "value": "collab"
                                    },
                                    {
                                        "title": "Data Center",
                                        "value": "dc"
                                    }
                                ]
                            },
                            {
                                "type": "Input.Text",
                                "id": "filter_flag",
                                "placeholder": "collab",
                                "value": ""
                            },
                            {
                                "type": "Input.Toggle",
                                "title": "Mobile?",
                                "value": "false",
                                "wrap": false,
                                "id" : "mobile_flag"
                            }

                                    ]
                                }
                            ]
                        }
                    ],
                    "actions": [
                        {
                            "type": "Action.Submit",
                            "title": "Submit"
                        }
                    ]
                }
        }
    ]
    }
                          
    """

    #room_id = "Y2lzY29zcGFyazovL3VzL1JPT00vYTNjMjZkODAtMzZjYi0xMWU5LTk5NWItYjc2YjYzMTg0MjRj"
    markdown = "This is mark down text [link](www.google.com)"
    version = "1.0"

    area_dict = {"south":["TX","AR","NC"],"west":["CA","OR"]}
    area_state_codes_list = []
    for area, states in area_dict.items():  
        state_value = " , ".join(states)
        area_state_codes_list.append(f'{{"title": "{area}","value": "{state_value}" }},')

    area_state_codes = "".join(area_state_codes_list)
    area_state_codes = area_state_codes[:-1] #remove last comma

    arch_options = [ #turn into global
        ("Cross Architecture",["cross arch","cross","arch"]),
        ("Security",["sec","security","cyber"]),
        ("Data Center",["dc","data","datacenter"]),
        ("Internet of Things (IoT)",["iot"]),
        ("Cloud",["cloud"]),
        ("Enterprise Network",["en","enterprise","routing","switching","sw","sda","dna","wireless"]),
        ("Collaboration",["collab","col","collaboration","colab","voice","video","webex","contact","cc","ucce","uccx"])

    ]    
    filter_list = []
    for arch in arch_options:  
        arch_value = arch[1][0].upper()
        filter_list.append(f'{{"title": "{arch_value}","value": "{arch[0]}" }},')

    filter_options = "".join(filter_list)
    filter_options = filter_options[:-1] #remove last comma    
    body = (
        f'{{"type": "ColumnSet","columns": [{{"type": "Column","width": 2,"items": ['
        f'{{"type": "TextBlock","text": "Events-tbd Bot","weight": "Bolder","size": "Medium"}},'
        f'{{"type": "TextBlock","text": "Enter a State Code from the list below:","isSubtle": true,"wrap": true}},'
        f'{{"type": "FactSet","facts": [{area_state_codes}],"id": "state_list"}},'
        f'{{"type": "TextBlock","text": "State Code","wrap": true}},'
        f'{{"type": "Input.Text","placeholder": "TX","id": "state_code"}},'
        f'{{"type": "Input.ChoiceSet","choices": [{filter_options}],"id":"filter_flag","title": "Chose tech filter","isMultiSelect": false,"value": ""}},'
        f'{{"type": "Input.Toggle","title": "Mobile?","value": "false","wrap": false,"id" : "mobile_flag"}}]}}]}}'
    )
    test_card_payload = (
        f'{{'
        f'"roomId": "{room_id}",'
        f'"markdown": "{markdown}",'
        f'"attachments": [{{'
        f'"contentType": "application/vnd.microsoft.card.adaptive",'
        f'"content": {{"$schema": "http://adaptivecards.io/schemas/adaptive-card.json","type": "AdaptiveCard",'
        f'"version": "{version}","body": [{body}],'
        f'"actions": [{{"type":"Action.Submit","title":"Submit"}}]'
        f'}} }} ] }}'

    )     
    #payload = {"roomId": room_id,"markdown": message}
    #response = requests.request("POST", URL, data=json.dumps(payload), headers=headers)
    response = requests.request("POST", URL, data=test_card_payload, headers=headers)
    return response


def bot_post_to_room(room_id, message, headers):
    print(f"msg byte size(UTF-8): {len(message.encode('utf-8'))} bytes")
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
        if response is not 200 from webex.  COme here and check error msg
        Based on error, send user a help msg in their room and send the dev's room
        the actual error msg.
        
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
    search_obj = re.search(r'7439|big',error["message"])
    if search_obj:
        message = "Too many results for Teams output, sending email instead:"
    else:
        message = "Looks like we've hit a snag! Sending feedback to the development team."
    bot_post_to_room(room_id,message,headers)


def communicate_to_user(ss_client,room_id,headers,bot_name,data,state_filter,arch_filter,mobile_filter=False,url_filter=False,help=False):
    if not help:
        if url_filter:
            #do something
            for i in data:
                if i["url"]:
                    print(f"{i['Event Name']}   {i['url']} ")
        if not mobile_filter:
            state_list_joined = " ".join(state_filter)

            #MULTI-PRINT
            #n = # of events per message. 50 seems to be the limit so setting it to 40 just for some room
            msg = format_code_print_for_bot(data,state_list_joined,CODE_PRINT_COLUMNS,msg_flag="start")
            response = bot_post_to_room(room_id, msg, headers)
            n = 40 #how large the data chunk to print
            for i in range(0, len(data), n):
                data_chunk = data[i:i + n]
                msg = format_code_print_for_bot(data_chunk,state_list_joined,CODE_PRINT_COLUMNS,msg_flag="data")
                response = bot_post_to_room(room_id, msg, headers)   
            msg = format_code_print_for_bot(data,state_list_joined,CODE_PRINT_COLUMNS,msg_flag="end")
            response = bot_post_to_room(room_id, msg, headers)                         

            msg = generate_html_table_for_bot(data,state_list_joined,EMAIL_COLUMNS)
            email_filename = generate_email(msg)
            response = bot_send_email(room_id,email_filename)  
        else:
            state_list_joined = " ".join(state_filter)

            msg = format_code_print_for_bot_mobile(data,state_list_joined,CODE_PRINT_COLUMNS_MOBILE, msg_flag="start")
            response = bot_post_to_room(room_id, msg, headers)

            n = 40 #how large the data chunk to print
            for i in range(0, len(data), n):
                data_chunk = data[i:i + n]
                msg = format_code_print_for_bot_mobile(data_chunk,state_list_joined,CODE_PRINT_COLUMNS_MOBILE,msg_flag="data")
                response = bot_post_to_room(room_id, msg, headers)   
            msg = format_code_print_for_bot_mobile(data,state_list_joined,CODE_PRINT_COLUMNS_MOBILE,msg_flag="end")
            response = bot_post_to_room(room_id, msg, headers)                   

    else:
        area_dict = get_all_areas_and_associated_states(ss_client,EVENT_SMARTSHEET_ID,AREA_COLUMN_FILTER)
        msg = format_help_msg(area_dict, bot_name)
        response = bot_post_to_room(room_id, msg, headers)          




