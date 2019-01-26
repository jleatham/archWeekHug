import os
import sys
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
from datetime import datetime
from operator import itemgetter
import json
from email import generator
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smartsheet


BOT_EMAIL = "hugtest@webex.bot"
BOT_NAME = "hugtest"
EVENT_SMARTSHEET_ID = "489009441990532"
EVENT_FORM_URL = "https://app.smartsheet.com/b/form/78ef07e1b4164f56ba8ac1aebd98f8f1"
event_area_column = "8697203800729476"
event_state_column = "6985264196282244"
AREA_COLUMN_FILTER = [event_area_column,event_state_column]
NO_COLUMN_FILTER = []

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
    area_dict = {}
    for key, value in temp_dict.items():
        area_dict[key] = list(set(value))
    return area_dict

def format_help_msg(area_dict):
    """
        Takes area_dict from above and formats the output using markdown codeblocks(```)
        area_dict looks like: {"south":["TX","AR","NC",etc],"west":["CA","OR",etc]} so need
        to join the states list into a string
        The markdown is also joined to a single string and returned to be printed
    """
    msg_list = []
    msg_list.append("``` \n")
    msg_list.append("Select State code from below\n\n")
    msg_list.append("Example:  {} events TX  \n".format(BOT_NAME))
    msg_list.append("Example:  {} events CA NV WA  \n\n".format(BOT_NAME))
    msg_list.append("{:<15}: {}  \n".format('Area', 'State Codes'))
    msg_list.append("{:*<15}: {:*<60}  \n".format('', ''))
    for area, states in area_dict.items():
        msg_list.append("{:<15}: {}  \n\n".format(area, ' , '.join(states)))
    msg_list.append("Created by Minh Nguyen (minhngu2) and Josh Leatham (jleatham) from Commercial South Area  \n")
    msg_list.append("  \n```")
    msg = ''.join(msg_list)
    return msg

def get_all_data_and_filter(ss_client,sheet_id,state,column_filter_list = []):
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
    return sorted_data

def format_code_print_for_bot(data,state):
    """
        Take pre-sorted data [{},{},{},..] and apply markdown
        Webex does not allow for large data table formatting so code blocks(```) are used as alternative.
        Output is one single long markdown string

        Should find a way to pass in column data as a list as opposed to hard coding
    """
    #python string formatting is useful: {:*<n.x} --> * = filler char, (<,>,or ^) = align left,right, or center, n.x = fill for n spaces, cut off after x
    msg_list = []
    msg_list.append("**Events for {}**  \n".format(state))
    #msg_list.append("Copy/Paste to download email template:   **{} {} email**  \n```".format(BOT_NAME,state))
    msg_list.append("Have an event to share?  Add it [here]({})  \n```".format(EVENT_FORM_URL))
    msg_list.append("  \n{:<60} {:<10} {:<4} {:<20} {:<10}".format('Event Name','Area','State','City','Event Date'))
    msg_list.append("  \n{:*<60} {:*<10} {:*<4} {:*<20} {:*<10}".format('*','*','*','*','*'))
    for row_dict in data:
        msg_list.append("  \n{:<60} {:<10} {:<4} {:<20} {:<10}".format(row_dict['Event Name'],row_dict['Area'],row_dict['State'],row_dict['City'],row_dict['Event Date']))

    msg_list.append("  \n```")
    msg = ''.join(msg_list)
    return msg

def generate_html_table_for_bot(data,state):
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
    column_names = [('Event Name','60'),('Informational Link','1'),('Event Type','5'),('State','5'),('City','10'),('Event Date','20'),('Event Lead','1')]
    msg_list = []
    msg_list.append("<h1>Events for {}</h1>".format(state))
    msg_list.append("<style type='text/css'>{}</style>".format(css['external']))
    msg_list.append("<table {}><thead><tr {}>".format(css['table'],css['tr']))
    for column, space in column_names:
        msg_list.append("<th {}><span {}>{}</span></th>".format(css['td'],css['span'],column))
    msg_list.append("</tr></thead>")
    msg_list.append("<tbody>")

    for row_dict in data:
        msg_list.append("<tr {}>".format(css['tr']))
        for column, space in column_names:
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
                    headers={'Authorization': os.environ['BOT_TOKEN'],
                    'Content-Type': m.content_type})
    return r.text