import os
import sys
from tornado import ioloop, web, websocket
import logging
import json
import pagan
import cStringIO
import base64
import names
import uuid
from itertools import ifilter
from collections import deque
from tornado.log import enable_pretty_logging

enable_pretty_logging()
logging.basicConfig(filename='logs/main.log',level=logging.DEBUG)


clients = []
messages = deque(maxlen=20)
COOKIE_USER_NAME = 'socket'

def get_user_id(clients, cookie_user):
    user_id = cookie_user
    if user_id is not None:
        if not check_auth(user_id):
            user_id = None
    return user_id or generate_token(clients)

def check_auth(token_id):
    #var set for example in bash or heroku app
    print os.environ.get("admin", '')
    return os.environ.get("admin", '') == token_id

def generate_token(clients):
    while True:
        token_id = uuid.uuid4().hex
        if next(ifilter(lambda x: x.user['id']==token_id, clients), False) == False:
            return token_id

def get_image(name=''):
    img = pagan.Avatar(name, pagan.SHA224)
    buffer = cStringIO.StringIO()
    img.img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue())

class SocketHandler(websocket.WebSocketHandler):
    user = None

    def check_origin(self, origin):
        return True

    def open(self):
        user_id = get_user_id(clients, self.get_cookie(COOKIE_USER_NAME, None))
        self.user = {'id': user_id, 'name': names.get_full_name(), 'avatar': get_image(unicode(user_id))}
        client = next(ifilter(lambda x: x.user['id']==user_id, clients), None) 
        if client is not None: 
            self.user = client.user
        else: 
            self.user = {'id': user_id, 'name': names.get_full_name(), 'avatar': get_image(unicode(user_id))} 
        clients.append(self)

        for c in clients:
            if c==self or client:
                c.write_message(json.dumps({'users': map(lambda x: x.user, clients), 'myself': user_id}))
            else:
                c.write_message(json.dumps({'user': self.user, 'cookie': COOKIE_USER_NAME}))
        for c in clients:
            for m in messages:
                c.write_message(json.dumps({'msg': m['msg'], 'sender': m['sender']}))
        print 'open', len(clients)

    def on_close(self):
        user_id = self.user['id']
        if self in clients:
            clients.remove(self)
        for c in clients:
            c.write_message(json.dumps({'user_remove': {'id': user_id}}))
        print 'close', len(clients), user_id

    def on_message(self, message):
        if message:
            messages.append({'msg': message, 'sender': self.user})
            for c in clients:
                if c != self:
                    c.write_message(json.dumps({'msg': message, 'sender': self.user}))
                else:
                    c.write_message(json.dumps({'received': True}))


class ApiHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        self.finish()
        for c in clients:
            c.write_message('{"msg": "hello"}')

    @web.asynchronous
    def post(self):
        pass


class MainHandler(web.RequestHandler):
    def get(self):
        self.write(json.dumps({'cookie_name': COOKIE_USER_NAME}))
 
app = web.Application([
    (r'/', MainHandler),
    (r'/ws', SocketHandler),
    (r'/api', ApiHandler),
], debug=True)

 
if __name__ == "__main__":
    app.listen(int(os.environ.get("PORT", 5000)))
    ioloop.IOLoop.instance().start()
