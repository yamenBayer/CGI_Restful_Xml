from datetime import datetime
import json
import os
import time
import urllib.request
import cv2
import numpy as np
from django.conf import settings
from pytz import utc
from dicttoxml import dicttoxml
from API.models import *
from API.serializers import Face_CollectionSerializer
import curlify

face_detection_pcDetector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml");
face_detection_webcamDetector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml");
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read('./API/trainer/trainer.yml')   #load trained model
cascadePath = "./API/haarcascade_frontalface_default.xml"
faceCascade = cv2.CascadeClassifier(cascadePath)
font = cv2.FONT_HERSHEY_SIMPLEX

class PcCamera(object):
    # Using frame for render
    frame = None
    # Using profile owner to save detected photos
    owner = None
    # Using flags for reconnecting and test the cameras if they are running
    flag = True
    exitFlag = False
    # The resquest
    request = None
    service_api_key = None
    # Initialize the object and starts the camera
    def __init__(self ,id, request, api_key):
        self.video = cv2.VideoCapture(0)
        try:
            profile = Profile.objects.get(id = id)
        except Profile.DoesNotExist:
            print('Profile Does Not Exist!')
        if profile:
            self.owner = profile
        if request:
            self.request = request
        if api_key:
            self.service_api_key = api_key

    # Destroy the object
    def __del__(self):
        self.flag = False
        self.exitFlag = True
        self.video.release()

    # Stop the functionality of the object
    def release(self):
        self.flag = False
        self.exitFlag = True
        self.video.release()
        print('Pc camera off')
        
    # Save the detected person with specific datetime
    def save(self, now, img , id):
        current_time = now.strftime("%d_%m_%Y_%H_%M_%S")
        path = './API/Face_Collection/detected.%s.png' % current_time
        cv2.imwrite(path, img)
        detected = Face_Collection(owner = self.owner,name = id, path = path, api_key = self.service_api_key)
        detected.save()

        dict = Face_CollectionSerializer(detected, many=False)
        js = json.dumps(dict.data)
        xml = dicttoxml(dict.data, custom_root='root', attr_type=False)
        
        detected.restful_response_json = str(js)
        detected.restful_response_xml = str(xml)
        detected.request = 'curl -X GET http://127.0.0.1:8000/api/face/{0}'.format(str(detected.id))
        detected.save()

    # gets the frame that comes from the camera
    def get_frame(self):
        ret, jpeg = cv2.imencode('.jpg', self.frame)
        return jpeg.tobytes()

    def getFlag(self):
        return self.flag

    def getExitFlag(self):
        return self.exitFlag

    # Living the camera with both detection and recognition algorithms
    def live(self, count, namesList):
        self.flag = True
        id = count # the number of people are stored in the database
        names = namesList  # names list of the people

        # Initialize and start realtime video capture
        self.video.set(3, 640) # set video widht
        self.video.set(4, 480) # set video height

        # Define min window size to be recognized as a face
        minW = 0.1*self.video.get(3)
        minH = 0.1*self.video.get(4)

        while True:
            if self.exitFlag == False:
                success, img =self.video.read()
                if success and self.flag:
                    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
                    faces = faceCascade.detectMultiScale( 
                        gray,
                        scaleFactor = 1.2,
                        minNeighbors = 5,
                        minSize = (int(minW), int(minH)),
                    )

                    for(x,y,w,h) in faces:

                        cv2.rectangle(img, (x,y), (x+w,y+h), (0,255,0), 2)

                        id, confidence = recognizer.predict(gray[y:y+h,x:x+w])
                        face_image = img[y:y + h, x:x + w]
                        # Check if confidence is less them 100 ==> "0" is perfect match 
                        if (confidence < 90 and id < len(names)):
                            id = names[id]
                            confidence = "  {0}%".format(round(100 - confidence))
                            # gets the time
                            now = datetime.now(utc) 
                            try:
                                # gets the last detected person from the database
                                person = Face_Collection.objects.latest('id')
                                last_detection = person.created_at
                                difference = now - last_detection
                                # if the last detected person was from 1 minute and his name is different save it
                                if difference.seconds > 60 or id != person.name:
                                    self.save(now, face_image, id)
                            except Exception:
                                    self.save(now, face_image, id)
    
                        else:
                            id = "unknown"
                            confidence = "  {0}%".format(round(100 - confidence))
                            now = datetime.now(utc) 
                            try:
                                person = Face_Collection.objects.latest('id')
                                last_detection = person.created_at
                                difference = now - last_detection
                                if difference.seconds > 1 or id != person.name:
                                    self.save(now, face_image, id)
                            except Exception:
                                    self.save(now, face_image, id)
                        
                        cv2.putText(img, str(id), (x+5,y-5), font, 1, (255,255,255), 2)
                        cv2.putText(img, str(confidence), (x+5,y+h-5), font, 1, (255,255,0), 1)  

                    self.frame = img
                else:
                    self.video = cv2.VideoCapture(0)
                    time.sleep(2)
                    self.flag = True
            else:
                break



class IPWebCam(object):
    frame = None
    owner = None
    flag = True
    exitFlag = False
    request = None
    ip = None
    service_api_key = None
 
    def __init__(self, camera_ip ,id, request,api_key):
        self.url = "http://"+camera_ip+"/shot.jpg"
        try:
            profile = Profile.objects.get(id = id)
        except Profile.DoesNotExist:
            print('Profile Does Not Exist!')
        if profile:
            self.owner = profile
        if request:
            self.request = request
        if camera_ip:
            self.ip = camera_ip
        if api_key:
            self.service_api_key = api_key

    def __del__(self):
        self.flag = False
        self.exitFlag = True
        pass        

    def release(self):
        self.flag = False
        self.exitFlag = True
    
    def save(self, now, img , id):
        current_time = now.strftime("%d_%m_%Y_%H_%M_%S")
        path = './API/Face_Collection/detected.%s.png' % current_time
        cv2.imwrite(path, img)

        detected = Face_Collection(owner = self.owner,name = id, path = path, api_key = self.service_api_key)
        detected.save()

        dict = Face_CollectionSerializer(detected, many=False)
        js = json.dumps(dict.data)
        xml = dicttoxml(dict.data, custom_root='root', attr_type=False)
        
        detected.restful_response_json = str(js)
        detected.restful_response_xml = str(xml)
        detected.request = 'curl -X GET http://127.0.0.1:8000/api/face/{0}'.format(str(detected.id))
        detected.save()

    def getFlag(self):
        return self.flag

    def getExitFlag(self):
        return self.exitFlag

    def get_frame(self):
        ret, jpeg = cv2.imencode('.jpg', self.frame)
        return jpeg.tobytes()


    def live(self, count, namesList):
        self.flag = True
        id = count
        names = namesList

        minW = 0.1*480
        minH = 0.1*640

        while True:
            if self.exitFlag == False:
                try:
                    imgResp = urllib.request.urlopen(self.url)
                    imgNp = np.array(bytearray(imgResp.read()),dtype=np.uint8)
                    img= cv2.imdecode(imgNp,-1)    
                    resize = cv2.resize(img, (640, 480), interpolation = cv2.INTER_LINEAR) 
                    frame_flip = cv2.flip(resize,1)

                    gray = cv2.cvtColor(frame_flip,cv2.COLOR_BGR2GRAY)

                    faces = faceCascade.detectMultiScale( 
                        gray,
                        scaleFactor = 1.2,
                        minNeighbors = 5,
                        minSize = (int(minW), int(minH)),
                    )

                    for(x,y,w,h) in faces:

                        cv2.rectangle(frame_flip, (x,y), (x+w,y+h), (0,255,0), 2)

                        id, confidence = recognizer.predict(gray[y:y+h,x:x+w])
                        face_image = frame_flip[y:y + h, x:x + w]
                        if (confidence < 90 and id < len(names)):
                            id = names[id]
                            confidence = "  {0}%".format(round(100 - confidence))
                            now = datetime.now(utc) 
                            try:
                                person = Face_Collection.objects.latest('id')
                                last_detection = person.created_at
                                difference = now - last_detection
                                if difference.seconds > 60 or id != person.name:
                                    self.save(now, face_image, id)
                            except Exception:
                                    self.save(now, face_image, id)
                            
                        else:
                            id = "unknown"
                            confidence = "  {0}%".format(round(100 - confidence))
                            now = datetime.now(utc) 
                            try:
                                person = Face_Collection.objects.latest('id')
                                last_detection = person.created_at
                                difference = now - last_detection
                                if difference.seconds > 60 or id != person.name:
                                    self.save(now, face_image, id)
                            except Exception:
                                    self.save(now, face_image, id)
                        
                        cv2.putText(frame_flip, str(id), (x+5,y-5), font, 1, (255,255,255), 2)
                        cv2.putText(frame_flip, str(confidence), (x+5,y+h-5), font, 1, (255,255,0), 1)  
                    
                    self.frame = frame_flip
                except Exception:
                    print('Failed to live from external camera > try to refresh the page or run the service!\nReconnecting...')
                    self.flag = False
                    time.sleep(2)
                    self.flag = True
            else:
                break

