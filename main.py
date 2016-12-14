import os
import sys
from tornado import ioloop, web, websocket
import logging

logging.basicConfig(filename='logs/main.log',level=logging.DEBUG)


cl = []

class SocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        logging.debug(self)
        cl.append(self)

    def on_close(self):
        if self in cl:
            cl.remove(self)


class ApiHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        self.finish()
        for c in cl:
            logging.debug(c)
            c.write_message('{"msg": "hello"}')

    @web.asynchronous
    def post(self):
        pass


class MainHandler(web.RequestHandler):
    def get(self):
        self.write("Hello world")
 
app = web.Application([
    (r'/', MainHandler),
    (r'/ws', SocketHandler),
    (r'/api', ApiHandler),
])

 
if __name__ == "__main__":
    app.listen(int(os.environ.get("PORT", 5000)))
    ioloop.IOLoop.instance().start()
