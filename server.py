import os
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.autoreload
import tornado.gen as gen
import cv2
import base64

from tornado.options import define, options, parse_command_line
from tornado.ioloop import PeriodicCallback

face_cascade = cv2.CascadeClassifier('/home/pi/FTP/tornado-chat/haarcascade_frontalface_default.xml')

define("port", default=8888, help="run on the given port", type=int)

# we gonna store clients in dictionary..
clients = set()

class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.render('index.html')        


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self, *args):
        clients.add(self) # add client for broadcasting

    def on_message(self, message):
        self.cam = cv2.VideoCapture(0)
        self.width = 640
        self.height = 480
        # set crop factor
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)        

        if message == "start":
            self.camera_loop = PeriodicCallback(self.loop, 100)
            self.camera_loop.start()
        else:
            print("Unsupported function: " + message)


    @gen.coroutine
    def loop(self):
        ret_val, imgread = self.cam.read()
        img = cv2.resize(imgread, (self.width, self.height), interpolation = cv2.INTER_AREA)

        cnt = cv2.imencode('.jpg', img)[1]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)
        try:
            ret, image = cv2.imencode('.jpg', img)
            self.write_message(base64.b64encode(cnt))
        except tornado.websocket.WebSocketClosedError:
            self.cam.release()

    def on_close(self):
        clients.remove(self)


app = tornado.web.Application([
    (r'/', IndexHandler),
    (r'/ws', WebSocketHandler),
])

if __name__ == '__main__':
    parse_command_line()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()