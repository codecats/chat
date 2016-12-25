import os
import sys
from tornado import ioloop, web, websocket
import logging
import json
import pagan
import cStringIO
import base64
import names

logging.basicConfig(filename='logs/main.log',level=logging.DEBUG)


clients = []
COOKIE_USER_NAME = 'socket'

def get_image(name=''):
    img = pagan.Avatar(name, pagan.SHA512)
    buffer = cStringIO.StringIO()
    img.img.save(buffer, format='JPEG')
    return base64.b64encode(buffer.getvalue())

class SocketHandler(websocket.WebSocketHandler):
    user = None

    def check_origin(self, origin):
        return True

    def open(self):
        user_id = self.get_cookie(COOKIE_USER_NAME)
        if not user_id:
            user_id = id(self)
        self.user = {'id': user_id, 'name': names.get_full_name(), 'avatar': get_image(unicode(user_id))}
        clients.append(self)

        for c in clients:
            if c==self:
                c.write_message(json.dumps({'users': map(lambda x: x.user, clients), 'myself': user_id}))
            else:
                c.write_message(json.dumps({'user': self.user, 'cookie': COOKIE_USER_NAME}))
        print 'open', len(clients)

    def on_close(self):
        user_id = self.get_cookie(COOKIE_USER_NAME, id(self))
        if self in clients:
            clients.remove(self)
        for c in clients:
            c.write_message(json.dumps({'user_remove': {'id': user_id}}))  
        print 'close', len(clients), user_id

    def on_message(self, message):
        if message:
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
