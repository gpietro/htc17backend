import os
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.autoreload
import tornado.gen as gen
import cv2
import base64
import smtplib
import datetime

from tornado.options import define, options, parse_command_line
from tornado.ioloop import PeriodicCallback

face_cascade = cv2.CascadeClassifier('/home/pi/FTP/htc17backend/haarcascade_frontalface_default.xml')
car_cascade = cv2.CascadeClassifier('/home/pi/FTP/htc17backend/cars.xml')

define("port", default=8888, help="run on the given port", type=int)

# we gonna store clients in dictionary..
clients = set()
last_alert = None
camera_loop = None
width = 640
height = 480        

cam = cv2.VideoCapture(0)        
# set crop factor
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)  

class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.render('index.html')        


class CoordinatesHandler(tornado.web.RequestHandler):    
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'GET')
        
    def get(self):
        # Hardcoded coordinates
        coordinates = [45.8367, 9.0246]
        self.write({'coordinates': coordinates})


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        super(WebSocketHandler, self).__init__(application, request, **kwargs)

    def check_origin(self, origin):
        return True

    def open(self, *args):
        clients.add(self) # add client for broadcasting
        
    def on_close(self):
        clients.remove(self)


@gen.coroutine
def loop():
    ret_val, img = cam.read()        

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cars = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    if len(cars) > 0:
        now = datetime.datetime.now()
        #send an alert every 5 minutes if vehicle still present
        ''' if not last_alert or last_alert < now - datetime.timedelta(minutes = 5):
            last_alert = now
            send_email(
                'hackthecity17', 
                'safecamproject', 
                ['pietroghezzi.ch@gmail.com', 'adriatik.dushica@gmail.com'],
                'Test', 
                'bella zio!!!'
            ) '''

    for (x, y, w, h) in cars:
        cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)
    try:            
        ret, image = cv2.imencode('.jpg', img)
        for client in clients:
            client.write_message(base64.b64encode(image))
    except tornado.websocket.WebSocketClosedError:
        cam.release()

@gen.coroutine
def send_email(user, pwd, recipient, subject, body):
    import smtplib

    gmail_user = user
    gmail_pwd = pwd
    FROM = 'Safe cam admin'
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = subject
    TEXT = body

    # Prepare actual message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(FROM, TO, message)
        server.close()
        print('successfully sent the mail')
    except:
        print('failed to send mail')

app = tornado.web.Application([
    (r'/', IndexHandler),
    (r'/coordinates', CoordinatesHandler),
    (r'/ws', WebSocketHandler),
])

if __name__ == '__main__':
    parse_command_line()
    app.listen(options.port)
    camera_loop = PeriodicCallback(loop, 40)
    camera_loop.start()
    tornado.ioloop.IOLoop.instance().start()