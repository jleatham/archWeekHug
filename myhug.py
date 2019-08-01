import hug
import os
import requests
import json
import re
from datetime import datetime
from operator import itemgetter
from botFunctions import TEST_EMAIL, TEST_NAME, EVENT_SMARTSHEET_ID, AREA_COLUMN_FILTER, NO_COLUMN_FILTER
from botFunctions import EVENTS_EMAIL, EVENTS_NAME
from botFunctions import CODE_PRINT_COLUMNS, EMAIL_COLUMNS
from botFunctions import ss_get_client, get_all_areas_and_associated_states
from botFunctions import format_help_msg,get_all_data_and_filter, format_code_print_for_bot
from botFunctions import generate_html_table_for_bot, map_cell_data_to_columnId
from botFunctions import generate_email, bot_send_email, send_log_to_ss
from state_codes import STATE_CODES


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
        command = command.lower()  #added this, don't forget to move to events-bot as well
        print("stripped command: {}".format(command))
        test2_process_bot_input_command(room_id,command, TEST_HEADERS, TEST_NAME)
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
    search_obj = re.search(r'7439',error["message"])
    if search_obj:
        message = "Too many results for Teams output, sending email instead:"
    else:
        message = "Looks like we've hit a snag! Sending feedback to the development team."
    bot_post_to_room(room_id,message,headers)



def test_process_bot_input_command(room_id,command, headers, bot_name):
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

    #use set(list).intersection(list2) to more easily compare commands given
    #for example if any word variation of security is used, append to the arch filter the specific
    #sec names used in smart sheet: 'Security' and 'Cyber Security'
    #should probably make this into a seperate function as well and return the arch_filter
    #match = list(set(command_list).intersection(sec_list))
    #if match:
        #arch_filter.append('Security','Cyber Security')
    #then loop through all different arch variations
    #once done, send the arch_filter to one of the functions to remove all other architectures
    event_list = ['events','Events','EVENTS','Event','event','EVENT']
    command_list = command.split(' ')
    arch_filter = check_command_for_arch(command_list)
    event_trigger = list(set(command_list).intersection(event_list))
    if event_trigger:
        for i in event_trigger:
            command = command.replace(i,'').strip()
        for i in arch_filter:
            command = command.replace(i,'').strip()
                
        state_list_joined = command
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
        if arch_filter:
            data = filter_data_by_architecture(data, arch_filter)
        msg = format_code_print_for_bot(data,state_list_joined,CODE_PRINT_COLUMNS)
        response = bot_post_to_room(room_id, msg, headers)
        msg = generate_html_table_for_bot(data,state_list_joined,EMAIL_COLUMNS)
        email_filename = generate_email(msg)
        response = bot_send_email(room_id,email_filename)        
    else:
        area_dict = get_all_areas_and_associated_states(ss_client,EVENT_SMARTSHEET_ID,AREA_COLUMN_FILTER)
        msg = format_help_msg(area_dict, bot_name)
        response = bot_post_to_room(room_id, msg, headers)

def check_command_for_arch(command_list):
    """
        Take command and search for posible architecture keywords such as 'security' or 'DC'
        Return the appropriate keyword used in smartsheets as a list
    """
    arch_filter = ['Cross Architecture'] #some arent provided,i.e., '', just don't include for now
    sec_list = ['security','Security','sec','Sec','SEC','SECURITY']
    dc_list = ['data','DATA','Data','datacenter','DataCenter','Datacenter','DATACENTER'] #can't do DC because it matches washington DC city
    collab_list = ['collab','Collab','COLLAB','collaboration','Collaboration','COLLABORATION','colab','Colab','COLAB']
    match = list(set(command_list).intersection(sec_list))
    if match:
        arch_filter.append('Security','Cyber Security')    
    match = list(set(command_list).intersection(dc_list))
    if match:
        arch_filter.append('Data Center')   
    match = list(set(command_list).intersection(collab_list))
    if match:
        arch_filter.append('Collaboration')  

    if len(arch_filter) <= 1:
        arch_filter = [] #clear out filter as no matches were found
    return arch_filter



#committing to master

#testing a better command processer
def test2_process_bot_input_command(room_id,command, headers, bot_name):
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
    data = []
    
    command_list = [
        ("events",['event','events','-e']),
        ("mobile",['mobile','phone','-m']),
        ("filter",['filter','-f'])
        #("command alias",["list of possible command entries"])
    ]
    result = command_parse(command_list,command)
    ##looks like: {"event":"TX FL AL","filter":"sec dc","mobile":""}
    if result:
        if "events" in result:
            print(f"made it to events:  {result['events']}") 
            state_filter = process_state_codes(result['events'])
        if "filter" in result:
            print(f"made it to filter:  {result['filter']}") 
            arch_filter = process_arch_filter(result['filter'])           
        if "mobile" in result:
            print(f"made it to mobile:  {result['mobile']}") 
            mobile_filter = True
                        
        data = test_get_all_data_and_filter(ss_client,EVENT_SMARTSHEET_ID, state_filter,arch_filter,NO_COLUMN_FILTER)
        communicate_to_user(ss_client,room_id,headers,data,state_filter,arch_filter,mobile_filter,help=False)
    else:
        communicate_to_user(ss_client,room_id,headers,data,state_filter,arch_filter,mobile_filter,help=True)      


def command_parse(command_list,command):
    #potential problem: city name has event / events or mobile or phone in it.  Could search for space or beginning of string to filter that out.
    """
        Takes a command_list (list of tuples), as well as a command(string coming from webex)
        Takes the string and find values in between the commands associated with each command
        Returns a dict that contains each command found as a key, and the args/values associated
        {"event":"TX FL AL","filter":"sec dc","mobile":""}
    """
    result = {}
    combined_command_list = []
    for i in command_list:
        for x in i[1]:
            combined_command_list.append(x)

    for i in command_list:
        command_hash = list(set(combined_command_list).symmetric_difference(i[1]))
        start_search = "|".join(i[1])
        end_search = "|".join(command_hash) + "|$"
        
        search = re.findall(r'('+start_search+')(.*?)('+end_search+')', command)
        if search:

            result[i[0]] = sanitize_commands(search[0][1])
    return result

def sanitize_commands(string):
    """
        Could do a lot here but don't right now.  Here is a good article on it:
        https://www.kdnuggets.com/2018/03/text-data-preprocessing-walkthrough-python.html
    """
    string = string.replace('\xa0','') #an artifact from WebEx sometimes
    string = string.replace(',',' ') #replace commas with spaces
    return string

def process_state_codes(string):
    """
        Goes through string (looks like: "tx fl al"), splits into a list, and capitalizes
        goes through each and finds the appropriate state for that state code
        Appends to list and returns
    """
    result = []
    string = string.upper()
    state_list = string.split(" ")
    for state in state_list:
        if state in STATE_CODES:
            result.append(STATE_CODES[state])
        else:
            result.append(state.capitalize())
    return result 

def process_arch_filter(string):
    """
        Take command and search for posible architecture keywords such as 'security' or 'DC'
        Return the appropriate keyword used in smartsheets as a list
    """
    arch_filter = []
    arch_options = [
        ("Cross Architecture",["cross","arch"]),
        ("Security",["sec","security","cyber"]),
        ("Cyber Security",["sec","security","cyber"]),
        ("Data Center",["data","dc","datacenter"]),
        ("Collaboration",["col","collab","collaboration","colab","voice","video","webex","contact","cc","ucce","uccx"])
        
    ]
    arch_list_provided = string.split(" ")
    for i in arch_list_provided:
        for y in arch_options:
            if i in y[1]:
                arch_filter.append(y[0])

    return arch_filter

def filter_data_by_architecture(data,arch_filter):
    """
        data is in a list of dicts [{'a1':'1','a2':'2'},{'b1':'1','b2':'2'}]
        remove if not in arch_filter
    """
    filtered_data = []
    for i in data:
        if i['Architecture'] in arch_filter:
            filtered_data.append(i)
    return filtered_data


def test_get_all_data_and_filter(ss_client,sheet_id,state,arch_filter,column_filter_list = []):
    """
        Sort through smartsheet and grab all data.  Use NO_COLUMN_FILTER to get all data
        Filter based on states provided, if date is in the future, and not cancelled
        Sort the data and return as a list of dictionaries, e.g., [{},{}]
        Each dict contains all columns and their associated value
    """
    #grab all smartsheet data and iterate through it
    sheet = ss_client.Sheets.get_sheet(sheet_id, column_ids=column_filter_list)
    all_data_list = []
    for row in sheet.rows:
        row_dict = {}
        for cell in row.cells:
            #map the column id to the column name
            #map the cell data to the column or '' if null
            column_title = map_cell_data_to_columnId(sheet.columns, cell)
            if cell.value:
                row_dict[column_title] = str(cell.value)
            else:
                row_dict[column_title] = ''
        #if event is virtual or in one of the states specified
        #AND if not cancelled AND if date is not in the past
        #then append whole row to the list as a dict
        if (row_dict['State'] in state or row_dict['Event Type'] == 'Virtual') and (row_dict['Event Status'] == 'Confirmed' and datetime.strptime(row_dict['Event Date'], '%Y-%m-%d') > datetime.now() ):
            if row_dict['Event Type'] == 'Virtual':
                row_dict['City'] = 'Virtual'
            all_data_list.append(row_dict)

    #sort data first by state, then by city, then by Date
    sorted_data = sorted(all_data_list, key=itemgetter('State','City','Event Date'))
    #Change date format and return
    for i in sorted_data:
        date_obj = datetime.strptime(i['Event Date'], '%Y-%m-%d')
        i['Event Date'] = datetime.strftime(date_obj, '%b %d, %Y')
    
    if arch_filter:
        sorted_data = filter_data_by_architecture(sorted_data,arch_filter)
    return sorted_data

def communicate_to_user(ss_client,room_id,headers,data,state_filter,arch_filter,mobile_filter=False,help=False):
    if not help:
        if not mobile_filter:
            state_list_joined = " ".join(state_filter)
            msg = format_code_print_for_bot(data,state_list_joined,CODE_PRINT_COLUMNS)
            response = bot_post_to_room(room_id, msg, headers)
            msg = generate_html_table_for_bot(data,state_list_joined,EMAIL_COLUMNS)
            email_filename = generate_email(msg)
            response = bot_send_email(room_id,email_filename)  
        else:
            print("need to figure this out later")
    else:
        area_dict = get_all_areas_and_associated_states(ss_client,EVENT_SMARTSHEET_ID,AREA_COLUMN_FILTER)
        msg = format_help_msg(area_dict, bot_name)
        response = bot_post_to_room(room_id, msg, headers)          
