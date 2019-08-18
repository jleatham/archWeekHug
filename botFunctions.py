import os
import sys
import requests
import re
from requests_toolbelt.multipart.encoder import MultipartEncoder
from datetime import datetime
from operator import itemgetter
import json
from email import generator
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smartsheet
from state_codes import STATE_CODES



BOT_EMAIL = "hugtest@webex.bot"
BOT_NAME = "hugtest"
TEST_EMAIL = os.environ['TEST_EMAIL']
TEST_NAME = os.environ['TEST_NAME']
EVENTS_EMAIL = os.environ['EVENTS_EMAIL']
EVENTS_NAME = os.environ['EVENTS_NAME']
#EVENT_SMARTSHEET_ID = "489009441990532"  #FY19
EVENT_SMARTSHEET_ID = "987451083777924"   #FY20
EVENT_FORM_URL = "https://app.smartsheet.com/b/form/78ef07e1b4164f56ba8ac1aebd98f8f1"

#FY19
#event_area_column = "8697203800729476"
#event_state_column = "6985264196282244"

#FY20
event_area_column = "797193901762436"
event_state_column = "6426693435975556"

AREA_COLUMN_FILTER = [event_area_column,event_state_column]
NO_COLUMN_FILTER = []
CODE_PRINT_COLUMNS = [('Event Name','60'),('State','8'),('City','20'),('Event Date','15'),('Architecture','25'),('Area','10')]
CODE_PRINT_COLUMNS_MOBILE = [('Event Name', '60'), ('State', '4'), ('City', '20'), ('Event Date', '15'), ('Architecture', '25'), ('Informational Link', '10'),('Area', '10')]
EMAIL_COLUMNS = [('Event Name','60'),('Informational Link','1'),('Architecture','5'),('State','5'),('City','10'),('Event Date','20'),('Event Lead','1')]

def ss_get_client(SMARTSHEET_TOKEN):
    #ss_client = smartsheet.Smartsheet(os.environ['SMARTSHEET_TOKEN'])
    ss_client = smartsheet.Smartsheet(SMARTSHEET_TOKEN)
    # Make sure we don't miss any errors
    ss_client.errors_as_exceptions(True)
    return ss_client

def get_all_areas_and_associated_states(ss_client,sheet_id,column_filter_list = []):
    """
        Sort through smartsheet and grab all Areas and their assosiated State Codes.
        Output will look like:  {"south":["TX","AR","NC",etc],"west":["CA","OR",etc]}
        Should update to not hardcode the columns to make function more reusable
    """
    #first pass, grab all the areas and put in list, then remove duplicates
    temp_area_list = []
    sheet = ss_client.Sheets.get_sheet(sheet_id, column_ids=column_filter_list)    
    for row in sheet.rows:
        temp_area_list.append(str(row.cells[0].value))
    area_list = list(set(temp_area_list))

    #prep data structure
    temp_dict = {}
    for area in area_list:
        #temp_dict looks like:  {"south":[],"west":[]}
        temp_dict[area] = []

    #second pass, append all states to their associated area and remove duplicates
    for row in sheet.rows:
        temp_dict[str(row.cells[0].value)].append(str(row.cells[1].value))
        #print(f"Data from sheets: key: {str(row.cells[0].value)}  value: {str(row.cells[1].value)}")
        #Looks like: Data from sheets: key: East  value: Maryland
    #print(f"Temp dict items: {temp_dict}")
    #Looks like: Temp dict items: {'All': ['Nevada', '--', '--', 'District of Columbia (DC)', 'California'],...
    area_dict = {}
    for key, value in temp_dict.items():
        value = process_state_codes(value,reverse=True)
        area_dict[key] = value
    #print(f"Final area_dict: {area_dict}")
    return area_dict


def format_help_msg(area_dict, bot_name, test_flag=False):
    """
        Takes area_dict from above and formats the output using markdown codeblocks(```)
        area_dict looks like: {"south":["TX","AR","NC",etc],"west":["CA","OR",etc]} so need
        to join the states list into a string
        The markdown is also joined to a single string and returned to be printed
    """

    if test_flag == True:
        msg_list = []
        msg_list.append("``` \\n\\n")
        msg_list.append("{:<15}: {}  \\n".format('Area', 'State Codes'))
        msg_list.append("{:*<15}: {:*<60}  \\n".format('', ''))
        for area, states in area_dict.items():
            msg_list.append("{:<15}: {}  \\n".format(area, ' , '.join(states)))
        msg_list.append("  \\nCreated by:")
        msg_list.append("  \\nMinh Nguyen (minhngu2) and Josh Leatham (jleatham) from Commercial South Area")
        msg_list.append("  \\n``` \\n\\n")
        msg_list.append(" # Commands for bot:  \\n")
        msg_list.append("Commands structure: events . . . filter . . . mobile  \\n")
        '''
        msg_list.append(" ### Examples:  \\n")
        msg_list.append("events|-e - -> state_code  \\n")
        msg_list.append("filter|-f - -> architectures you want to see  \\n")
        msg_list.append("mobile|-m - -> formats events to display on mobile  \\n")
        msg_list.append(" # Select State code from above  \\n")
        #add if else for whether bot is in space or 1 on 1.  No need for @ if 1 on 1
        msg_list.append("Remove the @{} when not in multi-user space (i.e., 1 on 1)  \\n".format(bot_name))
        msg_list.append("Example:  @{} **events TX**  \\n".format(bot_name))
        msg_list.append("Example:  @{} **events CA NV WA**  \\n".format(bot_name))    
        msg_list.append("Example:  @{} events CA NV WA filter sec  \\n".format(bot_name))   
        msg_list.append("Example:  @{} -e TX -f collab  \\n".format(bot_name)) 
        msg_list.append("Example:  @{} -events TX mobile  \\n".format(bot_name)) 
        '''
        msg = ''.join(msg_list)
        return msg
    else:
        msg_list = []     
        msg_list.append("``` \n\n")
        msg_list.append("{:<15}: {}  \n".format('Area', 'State Codes'))
        msg_list.append("{:*<15}: {:*<60}  \n".format('', ''))
        for area, states in area_dict.items():
            msg_list.append("{:<15}: {}  \n".format(area, ' , '.join(states)))
        msg_list.append("  \nCreated by:")
        msg_list.append("  \nMinh Nguyen (minhngu2) and Josh Leatham (jleatham) from Commercial South Area")
        msg_list.append("  \n``` \n\n")
        msg_list.append(" # Commands for bot:  \n")
        msg_list.append("Commands structure: \{events\} . . . \{filter\} . . . \{mobile\}  \n")
        msg_list.append("events|-e - -> state_code  \n")
        msg_list.append("filter|-f - -> architectures you want to see  \n")
        msg_list.append("mobile|-m - -> formats events to display on mobile  \n")
        msg_list.append(" # Select State code from above  \n")
        #add if else for whether bot is in space or 1 on 1.  No need for @ if 1 on 1
        msg_list.append("Remove the @{} when not in multi-user space (i.e., 1 on 1)  \n".format(bot_name))
        msg_list.append("Example:  @{} **events TX**  \n".format(bot_name))
        msg_list.append("Example:  @{} **events CA NV WA**  \n".format(bot_name))    
        msg_list.append("Example:  @{} events CA NV WA filter sec  \n".format(bot_name))   
        msg_list.append("Example:  @{} -e TX -f collab  \n".format(bot_name)) 
        msg_list.append("Example:  @{} -events TX mobile  \n".format(bot_name)) 
        msg = ''.join(msg_list)
        return msg

def get_all_data_and_filter(ss_client,sheet_id,state,arch_filter=False,url_filter=False,column_filter_list = []):
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
        row_dict["ss_row_id"] = str(row.id)
        row_dict["url"] = ""        
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
        try:
            if (row_dict['State'] in state or row_dict['Event Type'] == 'Virtual') and (row_dict['Event Status'] == 'Confirmed' and datetime.strptime(row_dict['Event Date'], '%Y-%m-%d') > datetime.now() ):
                if row_dict['Event Type'] == 'Virtual':
                    row_dict['City'] = 'Virtual'
                all_data_list.append(row_dict)
        except Exception as e:
            print(f"Error in event row:  {e}")
    
    
    '''
        Smartsheet API forces attachment to be aquired seperately
        First get all attachment IDs in the sheet, then grab the URL
        for each ID (with individual API call...)
    '''
    if url_filter:
        attachments = ss_client.Attachments.list_all_attachments(sheet_id)  
        for a in attachments.result:
            #print(dir(i))
            #print(i)
            attachment = ss_client.Attachments.get_attachment(sheet_id,a.id)
            for i in all_data_list:
                if i["ss_row_id"] == str(attachment.parent_id):
                    i["url"] = attachment.url    
    
    
    #sort data first by state, then by city, then by Date
    sorted_data = sorted(all_data_list, key=itemgetter('State','City','Event Date'))
    #Change date format and return
    for i in sorted_data:
        date_obj = datetime.strptime(i['Event Date'], '%Y-%m-%d')
        i['Event Date'] = datetime.strftime(date_obj, '%b %d, %Y')

    
    if arch_filter:
        sorted_data = filter_data_by_architecture(sorted_data,arch_filter)
    return sorted_data


def format_code_print_for_bot(data,state,columns,msg_flag):
    """
        Take pre-sorted data [{},{},{},..] and apply markdown
        Webex does not allow for large data table formatting so code blocks(```) are used as alternative.
        Output is one single long markdown string

        Should find a way to pass in column data as a list as opposed to hard coding
    """
    #python string formatting is useful: {:*<n.x} --> * = filler char, (<,>,or ^) = align left,right, or center, n.x = fill for n spaces, cut off after x

    #    print ("\n DATA \n")
    #    print (data)
    #    print ("\n COLUMNS \n")
    #    print (columns)
    msg_list = []
    if msg_flag == "start":
        msg_list.append("**Events for {}**  \n".format(state))
    elif msg_flag == "data":
        msg_list.append(" \n```")
        column_str, spacer_str = row_format_for_code_print(columns,header=True)
        msg_list.append(column_str)
        msg_list.append(spacer_str)       
        for row_dict in data:
            msg_list.append(row_format_for_code_print(columns,row_dict=row_dict))
        msg_list.append("  \n```")
    elif msg_flag == "end":
        msg_list.append("  \n ")
        msg_list.append("Commands structure: \{events\} . . . \{filter\} . . . \{mobile\}  \n")
        msg_list.append("Example:  :: events CA NV WA filter sec dc mobile  \n")   
        msg_list.append("Example:  :: -e TX -f collab  -m  \n") 
        msg_list.append("Example:  :: events TX mobile   \n") 
    msg = ''.join(msg_list)
    return msg


def row_format_for_code_print(columns,header=False,row_dict={}):
    """
        dymanically creates the table data based on a list of tuples
        e.g., column = [('Column Name','spacing integer'),(etc)]
        Columns and row data can be dynamically created from smartsheets if
        the column names are exact.
    """
    str_list = []
    str_list.append("  \n")
    #if printing table header
    if header == True:
        for column, space in columns:
            str_list.append("{c:<{s}} ".format(c=column,s=space))
    #else print the table data
    else:
        for column, space in columns:
            str_list.append("{c:<{s}} ".format(c=row_dict[column],s=space))
    
    str = ''.join(str_list)
    if header == True: 
        spacer_str =  "{:*<{s}}".format('  \n*',s=len(str))
        return str, spacer_str 
    else:
        return str


def generate_html_table_for_bot(data,state,columns):
    """
        Take pre-formatted data and prepare html data to be emailed
        Takes each row and adds to table with built in in-line CSS
        outputs the html as a string
    """
    
    css = {
        'external' : '.ExternalClass table, .ExternalClass tr, .ExternalClass td {line-height: 100%;}',
        'table' : 'width="100%" align="left" cellpadding="0" cellspacing="0" border="0px"',
        'tr' : 'style="margin:0px; padding:0px;border:none;align:left;"',
        'td' : 'style="border:none; margin:0px; padding:0px;align:left;"',
        'span' : 'style="display: block;text-align: left;margin:0px; padding:0px; "'
    }

    #using a list of tuples, the second item is not used today, but could be later if table percent widths need to be added
    msg_list = []
    msg_list.append("<h1>Events for {}</h1>".format(state))
    msg_list.append("<style type='text/css'>{}</style>".format(css['external']))
    msg_list.append("<table {}><thead><tr {}>".format(css['table'],css['tr']))
    for column, space in columns:
        msg_list.append("<th {}><span {}>{}</span></th>".format(css['td'],css['span'],column))
    msg_list.append("</tr></thead>")
    msg_list.append("<tbody>")

    for row_dict in data:
        msg_list.append("<tr {}>".format(css['tr']))
        for column, space in columns:
            if column == 'Informational Link':
                if row_dict[column]:
                    msg_list.append("<td><span {}><a href='{}'>Link</a></span></td>".format(css['span'],row_dict[column]))
                else:
                    msg_list.append("<td><span {}>{}</span></td>".format(css['span'],' '))
            else:
                msg_list.append("<td><span {}>{}</span></td>".format(css['span'],row_dict[column]))
        msg_list.append("</tr>")

    msg_list.append("</tbody>")
    msg_list.append("</table>")
    msg_list.append("<p></p>")
    msg = ''.join(msg_list)
    return msg

def map_cell_data_to_columnId(columns,cell):
    """
        helper function to map smartsheet column IDs to their name value without hardcoding
        pass in the parsed objects from smartsheet(the entire set of columns and the individual cell)
        then iterate until the ids match and return the associated column name
    """
    
    #cell object has listing for column_id , but data shows {columnId: n}, weird
    for column in columns:
        if column.id == cell.column_id:
            return column.title

def generate_email(msg):
    """
        Take the html data generated from smartsheet data and create an email
        file to be sent out as a .eml attachment
        return the temp name of the email file which right now is hardcoded
        and re-writen everytime the function is called
    """    
    
    html_data = """ <html><head></head><body>{}</body></html>""".format(msg)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = ""
    msg['From'] = ""
    msg['To'] = ""
    msg['Cc'] = ""
    msg['Bcc'] = ""

    part = MIMEText(html_data, 'html')
    msg.attach(part)

    outfile_name = "events_email.eml"
    with open(outfile_name, 'w') as outfile:
        gen = generator.Generator(outfile)
        gen.flatten(msg)  
    return outfile_name  

def bot_send_email(room_id, email_filename):
    """
        Sends the email file generated using MultipartEncoder which
        breaks the requests into tiny peices to get past the 5K Teams limit

    """
    m = MultipartEncoder({'roomId': room_id,
                      'text': 'Events email',
                      'files': (email_filename, open(email_filename, 'rb'),
                      'image/png')})
    r = requests.post('https://api.ciscospark.com/v1/messages', data=m,
                    headers={'Authorization': os.environ['EVENTS_TOKEN'],
                    'Content-Type': m.content_type})
    return r.text

def send_log_to_ss(bot_name,timestamp,identity,command,room_id):

    headers = {'Authorization': "Bearer "+os.environ['SMARTSHEET_TOKEN'],'Content-Type': "application/json"}
    url = "https://api.smartsheet.com/2.0/sheets/"+os.environ['SS_LOG_ID']+"/rows"    
    payload = '{"toBottom":true, "cells": [ \
                {"columnId": 6415325714507652,  "value": "'+ bot_name +'",    "strict": false}, \
                {"columnId": 4163525900822404, "value": "'+ timestamp +'",    "strict": false}, \
                {"columnId": 8667125528192900, "value": "'+ identity +'", "strict": false}, \
                {"columnId": 504351203583876, "value": "'+ command +'", "strict": false}, \
                {"columnId": 5007950830954372, "value": "'+ room_id +'", "strict": false} \
                ] }'     
    response = requests.request("POST", url, data=payload, headers=headers)
    responseJson = json.loads(response.text)
    #print(str(responseJson))


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
        #'(event|events|-e)(.*?)(-f|filter|-m|mobile)'
        #3 search groups in ()... interested in the second
        #when the command events is typed, regex will find event, strip the s, and put it as an arg...bug
        #I think that can be fixed by checking to make sure there is a space afterwards, but then what about
        #typing -m at the end of command, there won't be a space afterwards, and as this for loop progresses it
        #will place the -m at the start_search location. It won't detect it.  It will see the -m, it will see the 
        # end of string($), but it won't detect because the match because it would expect a -m_ with a space
        #I think I will just fix this in the sanitize command function by getting rid of single characters
        #
        #or i could just hard code a solution and strip S out of any result as I would never need it.  or likewise
        #just replace events with event before string goes through regex.
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
    string = ' '.join([w for w in string.split() if len(w)>1]) #remove all characters of length of 1
    return string

def process_state_codes(state_list,reverse=False):
    """
        Goes through string (looks like: "tx fl al"  ---- or reversed looks like: "Texas Florida Alabama") , splits into a list, and capitalizes
        goes through each and finds the appropriate state for that state code
        Appends to list and returns
    """
    result = []
    state_list = list(set(state_list))
    if not reverse:        
        for state in state_list:
            if state in STATE_CODES:
                result.append(STATE_CODES[state])
            else:
                result.append(state.capitalize())
        
    else:   
        for state in state_list:
            found = next((v for v, k in STATE_CODES.items() if k == state), None)
            if found:
                result.append(found)
            else:
                result.append(state)
        
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
        ("Internet of Things (IoT)",["iot"]),
        ("Cloud",["cloud"]),
        ("Enterprise Network",["en","enterprise","routing","switching","sw","sda","dna","wireless"]),
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



def format_code_print_for_bot_mobile(data,state,columns,msg_flag):
    """
        Take pre-sorted data [{},{},{},..] and apply markdown
        Webex does not allow for large data table formatting so code blocks(```) are used as alternative.
        Output is one single long markdown string

        Should find a way to pass in column data as a list as opposed to hard coding
    """
    print ("\n")
    print ("*** Entering Mobile Print ***")
    #python string formatting is useful: {:*<n.x} --> * = filler char, (<,>,or ^) = align left,right, or center, n.x = fill for n spaces, cut off after x
    msg_list = []
    column_str, spacer_str = row_format_for_code_print(columns,header=True)

    if msg_flag =="start":
        msg_list.append("**Events for {}**  \n\n ".format(state))
    elif msg_flag =="data":       
        for row_dict in data:
            msg_list.append(row_format_for_code_print_mobile(columns,row_dict=row_dict))
    elif msg_flag == "end":
        msg_list.append("  \n ")
        msg_list.append("Commands structure: \{events\} . . . \{filter\} . . . \{mobile\}  \n")
        msg_list.append("Example:  :: events CA NV WA filter sec dc mobile  \n")   
        msg_list.append("Example:  :: -e TX -f collab  -m  \n") 
        msg_list.append("Example:  :: events TX mobile   \n")  

    msg = ''.join(msg_list)
 #   print ("\n\n *** Broken Data ***")
 #   print (len(data))
 #   print ("\n\n")
#    print (msg_list)
    return msg
 


def row_format_for_code_print_mobile(columns,header=False,row_dict={}):
    """
        dymanically creates the table data based on a list of tuples
        e.g., column = [('Column Name','spacing integer'),(etc)]
        Columns and row data can be dynamically created from smartsheets if
        the column names are exact.
    """
    str_list = []

    #if printing table header
    
    if header == True:
        for column, space in columns:
            str_list.append("{c:<{s}} ".format(c=column,s=space))
                          
    #else print the table data
    else:
        for column, space in columns:
            if column == "Event Name":
                str_list.append("***{}***  \n ".format(row_dict[column]))
            elif column == "City":
                str_list.append("  •  **City:** {}  \n".format(row_dict[column]))
            elif column == "Event Date":
                str_list.append("  •  **Date:** {}  \n".format(row_dict[column]))
            elif column == "Architecture":
                str_list.append("  •  **Arch:** {}  \n".format(row_dict[column]))
            elif column == "Informational Link":
                if row_dict[column] == "":
                    str_list.append("\n")
                else:
                    str_list.append("  •  **Reg:** [Link]({})  \n\n".format(row_dict[column]))
            else:
               pass
  #              str_list.append("{c:<{s}} ".format(c=row_dict[column],s=space))
    #msg_list.append("Have an event to share?  Add it [here]({})  \n```".format(EVENT_FORM_URL))
  #          print (row_dict[column])
          #  print(str_list)
    str = ''.join(str_list)
    if header == True: 
        spacer_str =  "{:*<{s}}".format('  \n*',s=len(str))
        return str, spacer_str 
    else:
        return str
