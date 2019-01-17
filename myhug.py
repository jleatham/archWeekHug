"""First hug API (local and HTTP access)"""
import hug
import os
import requests
import json


bot_email = "hugtest@webex.bot"
bot_name = "hugtest"

# Webex variables
url = "https://api.ciscospark.com/v1/messages"
headers = {
    'Authorization': os.environ['BOT_TOKEN'],
    'Content-Type': "application/json",
    'cache-control': "no-cache"
}

@hug.get(examples='name=Timothy&age=26')
@hug.local()
def happy_birthday(name: hug.types.text, age: hug.types.number, hug_timer=3):
    """Says happy birthday to a user"""
    return {'message': 'Happy {0} Birthday {1}!'.format(age, name), 'took': float(hug_timer)}

@hug.get(examples='blah=whatever')
def echo(blah: hug.types.text,hug_timer=3):
    """Echos back whatever given"""
    return {'message': '{}'.format(blah), 'took': float(hug_timer)}

@hug.post('/hello', examples='hello')
def hello(body):
    """Test for webex teams"""
    print("GOT {}: {}".format(type(body), repr(body)))
    room_id = body["data"]["roomId"]
    identity = body["data"]["personEmail"]
    text = body["data"]["id"]
    if identity != bot_email:
        command = get_msg_sent_to_bot(text).lower()
        command = (command.replace(bot_name, '')).strip()
        print("stripped command: {}".format(command))



        if command in ("spiff","news","promo","services","partner","capital"):
            response = bot_post_to_room(room_id, command)
            print("botpost response: {}".format(response))
        else:
            msg = ("**Commands available**: < spiff >,< news >,< promo >,< services >,< partner >,< capital >  \n"
                   "*example*: {bot} news  \n"
                   "*example*: {bot} spiff  \n"
                   "\n\n**Filter results**: < en >,< collab >,< dc >,< sec >,< app >  \n"
                   "*example*: {bot} news en \n"
                   "*example*: {bot} spiff collab \n"
                   ).format(bot = bot_name)
            response = bot_post_to_room(room_id, msg)
            print("botpost response: {}".format(response))            
    #webex_post_example()
    #return {"roomId": roomId,"text": msg}
    #return
    
def bot_post_to_room(room_id, message):

    payload = {"roomId": room_id,"markdown": message}
    response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
    
    return response

def get_msg_sent_to_bot(msg_id):
    urltext = url + "/" + msg_id
    payload = ""

    response = requests.request("GET", urltext, data=payload, headers=headers)
    response = json.loads(response.text)
    #print ("Message to bot : {}".format(response["text"]))
    return response["text"]