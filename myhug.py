"""First hug API (local and HTTP access)"""
import hug


@hug.get(examples='name=Timothy&age=26')
@hug.local()
def happy_birthday(name: hug.types.text, age: hug.types.number, hug_timer=3):
    """Says happy birthday to a user"""
    return {'message': 'Happy {0} Birthday {1}!'.format(age, name), 'took': float(hug_timer)}

@hug.get(examples='blah=whatever')
def echo(blah: hug.types.text,hug_timer=3):
    """Echos back whatever given"""
    return {'message': '{}'.format(blah), 'took': float(hug_timer)}

@hug.get(examples='hello')
def hello():
    """Test for webex teams"""
    roomId = 'Y2lzY29zcGFyazovL3VzL1JPT00vNjg2YTkwODAtZmZjMy0xMWU4LWI0NTgtMzc2MWQzZGY5MjNj'
    msg = 'hello world'
    return {"roomId": roomId,"markdown": msg}
    