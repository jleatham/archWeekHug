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
from secrets import SPARK_ACCESS_TOKEN, SMARTSHEET_TOKEN, HUGTEST_ROOM_ID
#todo, integrate postgres on heroku and store smartsheet data
#https://stackoverflow.com/questions/20775490/how-to-create-or-manage-heroku-postgres-database-instance

'''
        #markdown help:
        #newline    -->|  \n      <--doublespaces required
        #paragraph  -->|\n\n
        #bold       -->|**Bolded Text**
        #italics    -->|*Italic Text*
        #hyperlink  -->|[link text](https://www.google.com)
        #numberlist -->|1. hello  \n2. bye  \n3. end
        #codeblock  -->|```hello  \nis this code  \nx.hello()  \nblah  \n```\n\n**not code**
        #mention    -->|<@personEmail:email@example.com|Joe> Whatup?
        msg = ("**Commands available**: < spiff >,< news >,< promo >,< services >,< partner >,< capital >  \n"
                "*example*: {bot} news  \n"
                "*example*: {bot} spiff  \n"
                "\n\n**Filter results**: < en >,< collab >,< dc >,< sec >,< app >  \n"
                "*example*: {bot} news en  \n"
                "*example*: {bot} spiff collab  \n"
                ).format(bot = bot_name)
        response = bot_post_to_room(room_id, msg)
'''


'''
               Global ID#  4434467927418756
     Event ID (from AFMC)  4914842529228676
                   SSID #  4170514429175684
               Event Name  4193604173358980
                     Area  8697203800729476
               Event Date  2481664568911748
             Event Status  2964285748995972
           Fiscal Quarter  4409256964319108
                     City  7289828917176196
                    State  6985264196282244
             Architecture  2786229289805700
                 Vertical  992286747191172
               Event Type  5859364289439620
           Event Strategy  5229449194039172
                 Audience  1355764662069124
        Cisco-Partner Led  5296414336018308
                  Segment  6589440010282884
            Select Region  1336420129367940
         Territory Region  792814708647812
            Local Contact  3607564475754372
               Event Lead  184410042591108
                 Comments  3547617704601476
        Registrant Report  4275694881531780
                 Password  8779294508902276
       Informational Link  1473495319242628
        Number Registered   78597282129796
          Number Attended  4582196909500292
             Attendance %  4172800626845572
             Hand Raisers  2232257990682500
            Modified Date  6422314242860932
              Modified By  1918714615490436
             Created Date  7548214149703556
               Created By  3044614522333060
'''

BOT_EMAIL = "hugtest@webex.bot"
BOT_NAME = "hugtest"
EVENT_SMARTSHEET_ID = "489009441990532"
arch_week_smartsheet_id = "2089577960761220"
#event_smartsheet_id = "489009441990532"
event_name_column = "4193604173358980"
event_area_column = "8697203800729476"
event_state_column = "6985264196282244"
AREA_COLUMN_FILTER = [event_area_column,event_state_column]
NO_COLUMN_FILTER = []
CODE_PRINT_COLUMNS = [('Event Name','60'),('State','4'),('City','20'),('Event Date','15'),('Architecture','25'),('Area','10')]
EMAIL_COLUMNS = [('Event Name','60'),('Informational Link','1'),('Architecture','5'),('State','5'),('City','10'),('Event Date','20'),('Event Lead','1')]

url = "https://api.ciscospark.com/v1/messages"
headers = {
    'Authorization': SPARK_ACCESS_TOKEN,
    'Content-Type': "application/json",
    'cache-control': "no-cache"
}

def main():
    ss_client = ss_get_client(SMARTSHEET_TOKEN)
    #area_dict = get_all_areas_and_associated_states(ss_client,EVENT_SMARTSHEET_ID,AREA_COLUMN_FILTER)
    #msg = format_help_msg(area_dict)
    #response = bot_post_to_room(HUGTEST_ROOM_ID, msg)

    column_filter_list = []
    state_list = ['TX','CA','KY','MN','MO','MI','OH','IL','IA','KS','CO','NE','WI','ND','ID']
    state_list_joined = ' '.join(state_list)
    data = get_all_data_and_filter(ss_client,EVENT_SMARTSHEET_ID, state_list,NO_COLUMN_FILTER)
    msg = format_code_print_for_bot(BOT_NAME,data,state_list_joined,CODE_PRINT_COLUMNS)
    response = bot_post_to_room(HUGTEST_ROOM_ID, msg)
    msg = generate_html_table_for_bot(data,state_list_joined,EMAIL_COLUMNS)
    email_filename = generate_email(msg)
    response = bot_send_email(HUGTEST_ROOM_ID,email_filename)

    

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
    temp_area_list = []

    sheet = ss_client.Sheets.get_sheet(sheet_id, column_ids=column_filter_list)
    #print("Full sheet size: {}       Filtered sheet size: {}".format(str(get_size(tempsheet)),str(get_size(sheet))))
    for row in sheet.rows:

        #print("{:<60} {:<10} {:<5}".format(str(row.cells[0].value),str(row.cells[1].value),str(row.cells[2].value)))
        temp_area_list.append(str(row.cells[0].value))
        #print(row.cells[2].value)
        #temp_dict[row.cells[0]].append(row.cells[1])
    area_list = list(set(temp_area_list))
    #print(area_list)
    temp_dict = {}
    for area in area_list:
        #temp_dict looks like:  {"south":[],"west":[]}
        temp_dict[area] = []
    for row in sheet.rows:
        temp_dict[str(row.cells[0].value)].append(str(row.cells[1].value))
    #print(str(temp_dict))
    area_dict = {}
    for key, value in temp_dict.items():
        area_dict[key] = list(set(value))
    #print(str(area_dict))
    return area_dict
        #should look like: {"south":["TX","AR","NC",etc],"west":["CA","OR",etc]}

def get_all_data_and_filter(ss_client,sheet_id,state,column_filter_list = []):
    sheet = ss_client.Sheets.get_sheet(sheet_id, column_ids=column_filter_list)
    
    all_data_list = []
    for row in sheet.rows:
        row_dict = {}
        
        for cell in row.cells:
        #for c in range(0, len(sheet.columns)):
            #print row.cells[c].value        
            column_title = map_cell_data_to_columnId(sheet.columns, cell)
            #if has hyperlink
            #elif has value


            if cell.value:
                row_dict[column_title] = str(cell.value)
            #else blank out with ''
            else:
                row_dict[column_title] = ''
        
        if (row_dict['State'] in state or row_dict['Event Type'] == 'Virtual') and (row_dict['Event Status'] == 'Confirmed' and datetime.strptime(row_dict['Event Date'], '%Y-%m-%d') > datetime.now() ):
            if row_dict['Event Type'] == 'Virtual':
                row_dict['City'] = 'Virtual'
            all_data_list.append(row_dict)

    sorted_data = sorted(all_data_list, key=itemgetter('State','City','Event Date'))
    for i in sorted_data:
        date_obj = datetime.strptime(i['Event Date'], '%Y-%m-%d')
        i['Event Date'] = datetime.strftime(date_obj, '%b %d, %Y')
        #print("{:<60} {:<10} {:<30} {:<10}".format(i['Event Name'],i['State'],i['City'],i['Event Date']))
    return sorted_data


def format_code_print_for_bot(BOT_NAME,data,state,columns):

    msg_list = []
    msg_list.append("**Events for {}**  \n".format(state))
    msg_list.append("Copy/Paste to download email template:   **{} {} email**  \n```".format(BOT_NAME,state))
    #msg_list.append("  \n{:<60} {:<10} {:<4} {:<20} {:<10}".format('Event Name','Area','State','City','Event Date'))
    #msg_list.append("  \n{:*<60} {:*<10} {:*<4} {:*<20} {:*<10}".format('*','*','*','*','*'))
    column_str, spacer_str = row_format_for_code_print(columns,header=True)
    msg_list.append(column_str)
    msg_list.append(spacer_str)    
    for row_dict in data:
        #msg_list.append("  \n{:<60} {:<10} {:<4} {:<20} {:<10}".format(row_dict['Event Name'],row_dict['Area'],row_dict['State'],row_dict['City'],row_dict['Event Date']))
        msg_list.append(row_format_for_code_print(columns,row_dict=row_dict))

    msg_list.append("  \n```")
    msg = ''.join(msg_list)
    print(msg)
    print(get_size(msg))
    #response = bot_post_to_room(HUGTEST_ROOM_ID, msg)
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
    
    css = {
        'external' : '.ExternalClass table, .ExternalClass tr, .ExternalClass td {line-height: 100%;}',
        'table' : 'width="100%" align="left" cellpadding="0" cellspacing="0" border="0px"',
        'tr' : 'style="margin:0px; padding:0px;border:none;align:left;"',
        'td' : 'style="border:none; margin:0px; padding:0px;align:left;"',
        'span' : 'style="display: block;text-align: left;margin:0px; padding:0px; "'
    }

    msg_list = []
    msg_list.append("<h1>Events for {}</h1>".format(state))
    msg_list.append("<style type='text/css'>{}</style>".format(css['external']))
    msg_list.append("<table {}><thead><tr {}>".format(css['table'],css['tr']))
    for column, space in columns:
        msg_list.append("<th {}><span {}>{}</span></th>".format(css['td'],css['span'],column))
    msg_list.append("</tr></thead>")
    msg_list.append("<tbody>")
    #msg_list.append("  \n{:<60} {:<10} {:<4} {:<10} {:<10}".format('Event Name','Area','State','City','Event Date'))
    #msg_list.append("  \n{:*<60} {:*<10} {:*<4} {:*<10} {:*<10}".format('*','*','*','*','*'))
    #msg_list.append("  \n{:<60}".format('[link text](https://www.google.com)'))
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
        #msg_list.append("  \n{:<60} {:<10} {:<4} {:<10} {:<10}".format(row_dict['Event Name'],row_dict['Area'],row_dict['State'],row_dict['City'],row_dict['Event Date']))
        msg_list.append("</tr>")

    msg_list.append("</tbody>")
    msg_list.append("</table>")
    msg_list.append("<p></p>")
    msg = ''.join(msg_list)
    print(msg)
    print(get_size(msg))
    #response = bot_post_to_room(HUGTEST_ROOM_ID, msg)
    return msg

def format_help_msg(area_dict):

    msg_list = []
    msg_list.append("``` \n")
    msg_list.append("Select State code from below\n\n")
    msg_list.append("Example:  {} TX  \n\n".format(BOT_NAME))
    msg_list.append("{:<15}: {}  \n".format('Area', 'State Codes'))
    msg_list.append("{:*<15}: {:*<60}  \n".format('', ''))
    for area, states in area_dict.items():
        msg_list.append("{:<15}: {}  \n".format(area, ' , '.join(states)))
    msg_list.append("  \n```")
    msg = ''.join(msg_list)
    #print(msg)
    #response = bot_post_to_room(HUGTEST_ROOM_ID, msg)
    return msg


#Code block version, how to get hyperlinks?
def test_print_state_events(ss_client,sheet_id,state):
    #is there a way to filter before grabbing?  not sure
    #i see a include=['filters], but don't see a way to define that
    #until then, grab all and filter myself
    sheet = ss_client.Sheets.get_sheet(sheet_id)
    
    msg_list = []
    msg_list.append("**Events for {}**  \n".format(state))
    msg_list.append("Copy/Paste to download email template:   **{} {} email**  \n```".format(BOT_NAME,state))
    msg_list.append("  \n{:<60} {:<10} {:<4} {:<20} {:<10}".format('Event Name','Area','State','City','Event Date'))
    msg_list.append("  \n{:*<60} {:*<10} {:*<4} {:*<20} {:*<10}".format('*','*','*','*','*'))
    for row in sheet.rows:
        row_dict = {}
        for cell in row.cells:
        #for c in range(0, len(sheet.columns)):
            #print row.cells[c].value        
            column_title = map_cell_data_to_columnId(sheet.columns, cell)
            #if has hyperlink
            #elif has value
            if cell.value:
                row_dict[column_title] = str(cell.value)
            #else blank out with ''
            else:
                row_dict[column_title] = ''
            #
        if row_dict['State'] == state:
            #msg_list.append("  \n")
            #for column, value in row_dict.items():
            #    if column in ('State','Event Name','Area'):
            #        msg_list.append("{} = {}    ".format(column, value))
            msg_list.append("  \n{:<60} {:<10} {:<4} {:<20} {:<10}".format(row_dict['Event Name'],row_dict['Area'],row_dict['State'],row_dict['City'],row_dict['Event Date']))
            #msg_list.append("  \n")
    msg_list.append("  \n```")
    msg = ''.join(msg_list)
    print(msg)
    print(get_size(msg))
    response = bot_post_to_room(HUGTEST_ROOM_ID, msg)
    #return msg

def test_dynamic_print_state_events(ss_client,sheet_id,state):
    #is there a way to filter before grabbing?  not sure
    #i see a include=['filters], but don't see a way to define that
    #until then, grab all and filter myself
    sheet = ss_client.Sheets.get_sheet(sheet_id)
    column_names = [('Event Name','60'),('Area','10'),('State','4'),('City','20'),('Event Date','10')]
    column_str = "  \n"
    for column, space in column_names:
        column_str.append("{c:<{s}} ".format(c=column,s=space))
    spacer_str =  "{:*<{s}}".format('  \n*',s=len(column_str))
    msg_list = []
    msg_list.append("**Events for {}**  \n".format(state))
    msg_list.append("Copy/Paste to download email template:   **{} {} email**  \n```".format(BOT_NAME,state))
    #msg_list.append("  \n{:<60} {:<10} {:<4} {:<20} {:<10}".format('Event Name','Area','State','City','Event Date'))
    #msg_list.append("  \n{:*<60} {:*<10} {:*<4} {:*<20} {:*<10}".format('*','*','*','*','*'))
    msg_list.append(column_str)
    msg_list.append(spacer_str)
    for row in sheet.rows:
        row_dict = {}
        for cell in row.cells:
        #for c in range(0, len(sheet.columns)):
            #print row.cells[c].value        
            column_title = map_cell_data_to_columnId(sheet.columns, cell)
            #if has hyperlink
            #elif has value
            if cell.value:
                row_dict[column_title] = str(cell.value)
            #else blank out with ''
            else:
                row_dict[column_title] = ''
            #
        if row_dict['State'] == state:
            #msg_list.append("  \n")
            #for column, value in row_dict.items():
            #    if column in ('State','Event Name','Area'):
            #        msg_list.append("{} = {}    ".format(column, value))
            msg_list.append("  \n{:<60} {:<10} {:<4} {:<20} {:<10}".format(row_dict['Event Name'],row_dict['Area'],row_dict['State'],row_dict['City'],row_dict['Event Date']))
            #msg_list.append("  \n")
    msg_list.append("  \n```")
    msg = ''.join(msg_list)
    print(msg)
    print(get_size(msg))
    response = bot_post_to_room(HUGTEST_ROOM_ID, msg)
    #return msg




#https://stackoverflow.com/questions/6046263/how-to-indent-a-few-lines-in-markdown-markup
#using <option + spacebar> to create a space that markdown does not ignore
#makes the request too large
def test_print_state_events_v2(ss_client,sheet_id,state):
    #is there a way to filter before grabbing?  not sure
    #i see a include=['filters], but don't see a way to define that
    #until then, grab all and filter myself
    sheet = ss_client.Sheets.get_sheet(sheet_id)
    
    msg_list = []
    msg_list.append("**Test State Print**  \n")
    msg_list.append("  \n{: <.10} | {: <20} | {: <8} | {: <20} | {: <20}".format('Event Name','Area','State','City','Event Date'))
    #msg_list.append("  \n{:<60}|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;| {:<10} |                          | {:<4} | {:<10} | {:<10}".format('Event Name','Area','State','City','Event Date'))
    msg_list.append("  \n{:*<60} {:*<10} {:*<4} {:*<10} {:*<10}".format('*','*','*','*','*'))
    #msg_list.append("  \n{:<60}".format('[link text](https://www.google.com)'))
    for row in sheet.rows:
        row_dict = {}
        for cell in row.cells:
        #for c in range(0, len(sheet.columns)):
            #print row.cells[c].value        
            column_title = map_cell_data_to_columnId(sheet.columns, cell)
            #if has hyperlink
            #elif has value
            if cell.value:
                row_dict[column_title] = str(cell.value)
            #else blank out with ''
            else:
                row_dict[column_title] = ''
            #
        if row_dict['State'] == state:
            #msg_list.append("  \n")
            #for column, value in row_dict.items():
            #    if column in ('State','Event Name','Area'):
            #        msg_list.append("{} = {}    ".format(column, value))
            
            msg_list.append("  \n{:_<40.40} {: <10.10} {: <10.10} {: <10.10} {: <10.10}".format(row_dict['Event Name'],row_dict['Area'],row_dict['State'],row_dict['City'],row_dict['Event Date']))
            
            #msg_list.append("  \n")
    msg_list.append("  \n")
    msg = ''.join(msg_list)
    print(msg)
    print(get_size(msg))
    response = bot_post_to_room(HUGTEST_ROOM_ID, msg)


def test_generate_html_table(ss_client,sheet_id,state):
    #is there a way to filter before grabbing?  not sure
    #i see a include=['filters], but don't see a way to define that
    #until then, grab all and filter myself
    '''
    css = {
        'trStyle' : 'style="background-color:transparent;"',
        'spanStyle' :  'style= "color:black;font-family:calibri,sans-serif;font-size:12pt;"',
        'tableStyle' : 'style="margin:5px;width:90%;border:2pt solid;cellpadding=0;cellspacing=0;border-radius:1px;font-family:-webkit-standard;letter-spacing:normal;orphans:auto;text-indent:0px;text-transform:none;widows:auto;word-spacing:0px;-webkit-text-size-adjust:auto;-webkit-text-stroke-width:0px;text-decoration:none;border-collapse:collapse;"',
        'tdStyleHeader' : 'style="text-align:left;border:2pt solid windowtext;padding:0in 5.4pt;vertical-align:top;"',
        'tdStyleBody' : 'style="width:100%;border-style:none solid;border-left-width:1pt;border-right-width:1pt;padding:0in 5.4pt;vertical-align:top;"',
        'spanStyleBlue' : 'style="color:#00b0f0;font-family:calibri,sans-serif;font-size:12pt;"',
        'aStyle' : 'style="color:rgb(149, 79, 114);text-decoration:underline;"',
        'tbodyStyle' : 'style=""'      
    }
    '''
    css = {
        'external' : '.ExternalClass * { line-height:105%; }',
        'trStyle' : 'style="margin:0px; padding:0px;"',
        'spanStyle' : 'style="margin:0px; padding:0px;"',
        'tableStyle' : 'style="width:100%; cellpadding:0px; cellspacing:0px; border:0px"',
        'tdStyleHeader' : 'style="margin:0px; padding:0px;"',
        'tdStyleBody' : 'style="margin:0px; padding:0px;"',
        'spanStyleBlue' : 'style="margin:0px; padding:0px;"',
        'tbodyStyle' : 'style="margin:0px; padding:0px;"' 

    }
    sheet = ss_client.Sheets.get_sheet(sheet_id)
    column_names = [('Event Name','60'),('Area','5'),('State','5'),('City','10'),('Event Date','20')]
    msg_list = []
    msg_list.append("<h1>Example Email</h1>")
    msg_list.append("<style type='text/css'>{}</style>".format(css['external']))
    msg_list.append("<table {}><thead><tr {}>".format(css['tableStyle'],css['trStyle']))
    for column, space in column_names:
        msg_list.append("<th {}><span {}>{}</span></th>".format(css['tdStyleHeader'],css['spanStyleBlue'],column))
    msg_list.append("</tr></thead>")
    msg_list.append("<tbody {}>".format(css['tbodyStyle']))
    #msg_list.append("  \n{:<60} {:<10} {:<4} {:<10} {:<10}".format('Event Name','Area','State','City','Event Date'))
    #msg_list.append("  \n{:*<60} {:*<10} {:*<4} {:*<10} {:*<10}".format('*','*','*','*','*'))
    #msg_list.append("  \n{:<60}".format('[link text](https://www.google.com)'))
    for row in sheet.rows:
        row_dict = {}
        
        for cell in row.cells:
        #for c in range(0, len(sheet.columns)):
            #print row.cells[c].value        
            column_title = map_cell_data_to_columnId(sheet.columns, cell)
            #if has hyperlink
            #elif has value
            if cell.value:
                row_dict[column_title] = str(cell.value)
            #else blank out with ''
            else:
                row_dict[column_title] = ''
            #
        msg_list.append("<tr {}>".format(css['trStyle']))
        if row_dict['State'] == state:
            for column, space in column_names:
                msg_list.append("<td><span {}>{}</span></td>".format(css['spanStyle'],row_dict[column]))
            #msg_list.append("  \n{:<60} {:<10} {:<4} {:<10} {:<10}".format(row_dict['Event Name'],row_dict['Area'],row_dict['State'],row_dict['City'],row_dict['Event Date']))
        msg_list.append("</tr>")

    msg_list.append("</tbody>")
    msg_list.append("</table>")
    msg_list.append("<p></p>")
    msg = ''.join(msg_list)
    print(msg)
    print(get_size(msg))
    #response = bot_post_to_room(HUGTEST_ROOM_ID, msg)
    return msg

def test_generate_html_table_v2(ss_client,sheet_id,state):
    msg = '''
                <style type="text/css">
            .ExternalClass table, .ExternalClass tr, .ExternalClass td {line-height: 100%;}
            </style>

            <table width="400" align="left" cellpadding="0" cellspacing="0" border="1">
            <tr style="margin:0px; padding:0px;">
                <td width="10" align="right" valign="top" style="border:none; margin:0px; padding:0px;">
                <span style="margin:0px; padding:0px;">
                &bull;
                </span>
                </td>
                <td width="380" align="left" valign="top" style="border:none; margin:0px; padding:0px;">
                <span style="margin:0px; padding:0px;">
                Info next to bullet
                </span>
                </td>
            </tr>
            <tr style="margin:0px; padding:0px;">
                <td width="10" align="right" valign="top" style="border:none; margin:0px; padding:0px;">
                <span style="margin:0px; padding:0px;">
                &bull;
                </span>
                </td>
                <td width="380" align="left" valign="top" style="border:none; margin:0px; padding:0px;">
                <span style="margin:0px; padding:0px;">
                Info next to bullet
                </span>
                </td>
            </tr>
            </table>
            '''
    return msg

def test_generate_html_table_v3(ss_client,sheet_id,state):
    
    css = {
        'external' : '.ExternalClass table, .ExternalClass tr, .ExternalClass td {line-height: 100%;}',
        'table' : 'width="100%" align="left" cellpadding="0" cellspacing="0" border="0px"',
        'tr' : 'style="margin:0px; padding:0px;border:none;align:left;"',
        'td' : 'style="border:none; margin:0px; padding:0px;align:left;"',
        'span' : 'style="display: block;text-align: left;margin:0px; padding:0px; "'
    }
    sheet = ss_client.Sheets.get_sheet(sheet_id)
    column_names = [('Event Name','60'),('Informational Link','1'),('Event Type','5'),('State','5'),('City','10'),('Event Date','20'),('Event Lead','1')]
    msg_list = []
    msg_list.append("<h1>Events for {}</h1>".format(state))
    msg_list.append("<style type='text/css'>{}</style>".format(css['external']))
    msg_list.append("<table {}><thead><tr {}>".format(css['table'],css['tr']))
    for column, space in column_names:
        msg_list.append("<th {}><span {}>{}</span></th>".format(css['td'],css['span'],column))
    msg_list.append("</tr></thead>")
    msg_list.append("<tbody>")
    #msg_list.append("  \n{:<60} {:<10} {:<4} {:<10} {:<10}".format('Event Name','Area','State','City','Event Date'))
    #msg_list.append("  \n{:*<60} {:*<10} {:*<4} {:*<10} {:*<10}".format('*','*','*','*','*'))
    #msg_list.append("  \n{:<60}".format('[link text](https://www.google.com)'))
    for row in sheet.rows:
        row_dict = {}
        
        for cell in row.cells:
        #for c in range(0, len(sheet.columns)):
            #print row.cells[c].value        
            column_title = map_cell_data_to_columnId(sheet.columns, cell)
            #if has hyperlink
            #elif has value


            if cell.value:
                row_dict[column_title] = str(cell.value)
            #else blank out with ''
            else:
                row_dict[column_title] = ''
            #
        msg_list.append("<tr {}>".format(css['tr']))
        if row_dict['State'] == state and row_dict['Event Status'] == 'Confirmed':
            for column, space in column_names:
                if column == 'Informational Link':
                    if row_dict[column]:
                        msg_list.append("<td><span {}><a href='{}'>Link</a></span></td>".format(css['span'],row_dict[column]))
                    else:
                        msg_list.append("<td><span {}>{}</span></td>".format(css['span'],' '))
                else:
                    msg_list.append("<td><span {}>{}</span></td>".format(css['span'],row_dict[column]))
            #msg_list.append("  \n{:<60} {:<10} {:<4} {:<10} {:<10}".format(row_dict['Event Name'],row_dict['Area'],row_dict['State'],row_dict['City'],row_dict['Event Date']))
        msg_list.append("</tr>")

    msg_list.append("</tbody>")
    msg_list.append("</table>")
    msg_list.append("<p></p>")
    msg = ''.join(msg_list)
    print(msg)
    print(get_size(msg))
    #response = bot_post_to_room(HUGTEST_ROOM_ID, msg)
    return msg


def map_cell_data_to_columnId(columns,cell):
    #cell object has listing for column_id , but data shows {columnId: n}, weird
    for column in columns:
        #print("{:>25}  {:>15}".format(str(column.title),str(column.id)))
        #print(str(cell))
        #print(type(columnId))
        #print(str(columnId))
        #print(columnId)
        #print(cell['columnId'])
        #print(cell.column_id)

        if column.id == cell.column_id:
            #print("found")
            return column.title
        

'''
def bot_post_to_room(room_id, message):

    payload = {"roomId": room_id,"markdown": message}
    response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
    response = json.loads(response.text)
    print("botpost response: {}".format(response)) 
    return response["text"]
'''
def bot_post_to_room(room_id, message):
    #try to post
    payload = {"roomId": room_id,"markdown": message}
    response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
    #error handling
    if response.status_code != 200:
        #modify function to receive user_input as well so we can pass through
        user_input = "some test message for the moment"
        #send to the DEVs bot room
        error_handling(response,response.status_code,user_input,room_id)


      


def error_handling(response,err_code,user_input,room_id):

    error = json.loads(response.text) #converts to type DICT
    #grabs the error response from teams
    #Example: {"message":"Unable to post message to room: \"The request payload is too big\"",
    #"errors":[{"description":"Unable to post message to room: \"The request payload is too big\""}],
    # "trackingId":"ROUTER_5C5510D1-D8A4-01BB-0055-48A302E70055"}

    #send to DEVs bot room
    message = ("**Error code**: {}  \n**User input**: {}  \n**Error**: {}".format(err_code,user_input,error["message"]))
    bot_post_to_room(HUGTEST_ROOM_ID,message)
    
    #need to add error handling here
    #if XYZ in response.text then, etc
    message = "Looks like we've hit a snag! Sending feedback to the development team."
    bot_post_to_room(room_id,message)



def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size 

def generate_email(msg):
    html_data = """ <html><head></head><body>{}</body></html>""".format(msg)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = ""
    msg['From'] = ""
    msg['To'] = ""
    msg['Cc'] = ""
    msg['Bcc'] = ""
    """
    headers = ... dict of header key / value pairs ...
    for key in headers:
        value = headers[key]
        if value and not isinstance(value, basestring):
            value = str(value)
        msg[key] = value
    """
    part = MIMEText(html_data, 'html')
    msg.attach(part)

    #outfile_name = os.path.join("/", "temp", "email_sample.eml")
    outfile_name = "temp_email.eml"
    with open(outfile_name, 'w') as outfile:
        gen = generator.Generator(outfile)
        gen.flatten(msg)  
    return outfile_name  

def bot_send_email(room_id, email_filename):
    m = MultipartEncoder({'roomId': room_id,
                      'text': 'Events email',
                      'files': (email_filename, open(email_filename, 'rb'),
                      'image/png')})
    r = requests.post('https://api.ciscospark.com/v1/messages', data=m,
                    headers={'Authorization': SPARK_ACCESS_TOKEN,
                    'Content-Type': m.content_type})
    print (r.text)
    #payload = {"roomId": room_id,"markdown": message}
    #response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
    #response = json.loads(response.text)
    #print("botpost response: {}".format(response)) 
    #return response["text"]
    return r.text

if __name__ == "__main__":
    main()