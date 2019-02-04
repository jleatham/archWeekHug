import test
from secrets import SPARK_ACCESS_TOKEN, SMARTSHEET_TOKEN, HUGTEST_ROOM_ID


#Use HUGTEST_ROOM_ID as our personal room for bot to send error messages to

#for user input: force lower case of the input so we don't have to account for any format of "events" - Events, EvEnts, EVEnts etc
#line 44 in myhug.py
# trigger[0].lower()
#if trigger[0] in ("event","events")



""""
Error handling
in bot_post_to_room method
> Check response.status_code != 200 (200 is successful request)
>> if response.status_code = 200 --> execute error_handling method
    within error_handling
        1. Send to our personal room:
            Error code:
            User input: (need to pass user input into method)
            Error: 
            POST message to our personal room
""""



def error_handling(response,err_code,user_input):

    response = json.loads(response.text) #converts to type DICT
    #grabs the error response from teams
    #Example: {"message":"Unable to post message to room: \"The request payload is too big\"",
    #"errors":[{"description":"Unable to post message to room: \"The request payload is too big\""}],
    # "trackingId":"ROUTER_5C5510D1-D8A4-01BB-0055-48A302E70055"}

    message = ("Error code: {} \n User input: {} \n Error:".format(err_code,user_input,response["message"]))
    bot_post_to_room(HUGTEST_ROOM_ID,message)
    
    return response["message"]


def bot_post_to_room(room_id, message):

    payload = {"roomId": room_id,"markdown": message}
    response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
    
    if response.status_code != 200
        error_handling(response,response.status_code,user_input)
        return "Looks like we've hit a snag! Sending feedback to the development team."
    else
        response = json.loads(response.text)


    #print("botpost response: {}".format(response)) 
    return response["text"]


""""
FEEDBACK function
1. We can create a list for outstanding feedbacks or improvements to the bot with a hidden delete command that allows us to delete 

@hugtest feedback please add achitecture columns
> take feedback comment and append to a list
> capture feedback and who sent
> writes to a file incase bot restarts

hidden commands:
> @hugtest feedback list - list out all feedback items in numerical code block
> @hugtest feedback delete <#> - deletes item from Feedback list. We can make sure this method only runs by you and I (check "personEmail")

within def process_bot_input_command(room_id,command):

else if trigger[0] = "feedback":
    feedback(trigger[1:]) #I believe this captures the rest of the information after trigger.split(" ")



def feedback(message):
    items = []
    msg = ""
    file = open("feedback.txt", "r")

    if message[0] = "list"
        msg = "```\n"
        msg.append(file.read())
 #       for line in file:
 #           msg.append(line)
        msg.append("  \n```")
        bot_post_to_room(HUGTEST_ROOM_ID,msg)
    
    elif message[0] = "delete":
        try:
            index = message[1]
            for line in file:
                msg.append(line)
                if message[1] == 0:
                    msg = "Not a valid index"
                else:
                    msg.pop(message[1]-1)
                    file.write(msg)
                    msg = "Successfully removed \n ```"
                    msg.append(file.read())
                    msg.append(" \n```)
                bot_post_to_room(HUGTEST_ROOM_ID,msg)

        except IndexError:
            msg = "Not a valid index"
            bot_post_to_room(HUGTEST_ROOM_ID,msg)

    else:
        items.append()
        file = open(feedback.txt, "a")
        file.write()


""""
