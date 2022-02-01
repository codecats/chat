"""Chat server main module."""
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
logging.basicConfig(filename="logs/main.log", level=logging.DEBUG)


# container for connected clients
clients = []
# limited message memory
messages = deque(maxlen=20)
COOKIE_USER_NAME = "socket"


def get_user_id(clients, cookie_user):
    """Get user ID from cookie or generate a new token."""
    user_id = cookie_user
    if user_id is not None:
        if not check_auth(user_id):
            user_id = None
    return user_id or generate_token(clients)


def check_auth(token_id):
    """Check if user is authenticated based on os ENV token."""
    # var set for example in bash or heroku app
    return os.environ.get("admin", "") == token_id


def generate_token(clients):
    """Generate unique token."""
    while True:
        token_id = uuid.uuid4().hex
        if next(ifilter(lambda x: x.user["id"] == token_id, clients), False) == False:
            return token_id


def get_image(name=""):
    """Get random generated avatar."""
    img = pagan.Avatar(name, pagan.SHA224)
    buffer = cStringIO.StringIO()
    img.img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue())


class SocketHandler(websocket.WebSocketHandler):
    """Socket handler class.

    This class is responsible for:
     - opening websocket connection
     - closing connection
     - passing messages to connected clients
    The message propagation uses JSON format. All user data is stored in
    memory, so all data is lost when the process is terminated. Clients can
    see chat history limitied to some messages described in the messages
    container.

    """

    user = None

    def check_origin(self, origin):
        """Check origin always true."""
        return True

    def open(self):
        """Open a new websocket connection.

        Assign user data like user ID, random name and image. Register user in
        the clients container and propagate message."""
        user_id = get_user_id(clients, self.get_cookie(COOKIE_USER_NAME, None))
        self.user = {
            "id": user_id,
            "name": names.get_full_name(),
            "avatar": get_image(unicode(user_id)),
        }
        client = next(ifilter(lambda x: x.user["id"] == user_id, clients), None)
        # check if already existing user (new tab)
        if client is not None:
            self.user = client.user
        else:
            self.user = {
                "id": user_id,
                "name": names.get_full_name(),
                "avatar": get_image(unicode(user_id)),
            }
        clients.append(self)

        # propagate messages
        for c in clients:
            if c == self or client:
                c.write_message(
                    json.dumps(
                        {"users": map(lambda x: x.user, clients), "myself": user_id}
                    )
                )
            else:
                c.write_message(
                    json.dumps({"user": self.user, "cookie": COOKIE_USER_NAME})
                )
        for m in messages:
            self.write_message(json.dumps({"msg": m["msg"], "sender": m["sender"]}))

    def on_close(self):
        """Close connection, remove user from the container."""
        user_id = self.user["id"]
        if self in clients:
            clients.remove(self)
        for c in clients:
            c.write_message(json.dumps({"user_remove": {"id": user_id}}))

    def on_message(self, message):
        """Propagate message to the connected clients."""
        if message:
            messages.append({"msg": message, "sender": self.user})
            for c in clients:
                # send the message to the client or just acknowledge the author
                # so he can see if the message was delivered
                if c != self:
                    c.write_message(json.dumps({"msg": message, "sender": self.user}))
                else:
                    c.write_message(json.dumps({"received": True}))


class ApiHandler(web.RequestHandler):
    """Asynchronous request."""

    @web.asynchronous
    def get(self, *args):
        """Send testing message to all the clients."""
        self.finish()
        for c in clients:
            c.write_message('{"msg": "hello"}')

    @web.asynchronous
    def post(self):
        """Post method must be defined"""


class MainHandler(web.RequestHandler):
    """Main server class is responsible for static data."""

    def get(self):
        """Return cookie in order to identify user's session."""
        self.write(json.dumps({"cookie_name": COOKIE_USER_NAME}))


app = web.Application(
    [
        (r"/", MainHandler),
        (r"/ws", SocketHandler),
        (r"/api", ApiHandler),
    ],
    debug=True,
)


if __name__ == "__main__":
    app.listen(int(os.environ.get("PORT", 5000)))
    ioloop.IOLoop.instance().start()
