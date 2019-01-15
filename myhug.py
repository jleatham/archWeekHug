"""First hug API (local and HTTP access)"""
import hug
import os
import requests




@hug.get(examples='name=Timothy&age=26')
@hug.local()
def happy_birthday(name: hug.types.text, age: hug.types.number, hug_timer=3):
    """Says happy birthday to a user"""
    return {'message': 'Happy {0} Birthday {1}!'.format(age, name), 'took': float(hug_timer)}

@hug.get(examples='blah=whatever')
def echo(blah: hug.types.text,hug_timer=3):
    """Echos back whatever given"""
    return {'message': '{}'.format(blah), 'took': float(hug_timer)}

@hug.post(examples='hello')
def hello(data):
    """Test for webex teams"""
    print(str(data))
    roomId = 'Y2lzY29zcGFyazovL3VzL1JPT00vNjg2YTkwODAtZmZjMy0xMWU4LWI0NTgtMzc2MWQzZGY5MjNj'
    msg = 'hello world'
    #webex_post_example()
    return {"roomId": roomId,"text": msg}
    
def webex_post_example():
    os.environ['BOT_TOKEN']
    url = "https://api.ciscospark.com/v1/messages"

    payload = "{\r\n  \"roomId\" : \"Y2lzY29zcGFyazovL3VzL1JPT00vNjg2YTkwODAtZmZjMy0xMWU4LWI0NTgtMzc2MWQzZGY5MjNj\",\r\n  \"text\" : \"hi from hug\"\r\n}"
    headers = {
        'Authorization': os.environ['BOT_TOKEN'],
        'Content-Type': "application/json"
        }

    response = requests.request("POST", url, data=payload, headers=headers)

    print(response.text)  
    #comment  
    return