from datetime import datetime
import cv2
import numpy as np
from PIL import Image
import urllib.request
from API.serializers import Face_CollectionSerializer
import json

from pytz import utc
from API.models import Face_Collection
from dicttoxml import dicttoxml
import curlify

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read('./API/trainer/trainer.yml')   #load trained model
cascadePath = "./API/haarcascade_frontalface_default.xml"
faceCascade = cv2.CascadeClassifier(cascadePath)
font = cv2.FONT_HERSHEY_SIMPLEX

def save(request, service_api_key, owner, now, img , id):
    try:
        current_time = now.strftime("%d_%m_%Y_%H_%M_%S")
        path = './API/Face_Collection/detected.%s.png' % current_time
        cv2.imwrite(path, img)
        detected = Face_Collection(owner = owner,name = id, path = path, api_key = service_api_key)
        detected.save()

        dict = Face_CollectionSerializer(detected, many=False)
        js = json.dumps(dict.data)
        xml = dicttoxml(dict.data, custom_root='root', attr_type=False)

        detected.restful_response_json = str(js)
        detected.restful_response_xml = str(xml)
        detected.request = 'curl -X GET http://127.0.0.1:8000/api/face/{0}'.format(str(detected.id))
        detected.save()

        return detected
    except:
        print('Face not saved!')
        raise

def webcam_recognize(ip, count, namesList):
    url = "http://"+ip+"/shot.jpg"
    id = count
    names = namesList

    minW = 0.1*480
    minH = 0.1*640

    while True:
        imgResp = urllib.request.urlopen(url)
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

            if (confidence < 90 and id < len(names)):
                id = names[id]
                confidence = "  {0}%".format(round(100 - confidence))
                
            else:
                id = "unknown"
                confidence = "  {0}%".format(round(100 - confidence))
            
            cv2.putText(frame_flip, str(id), (x+5,y-5), font, 1, (255,255,255), 2)
            cv2.putText(frame_flip, str(confidence), (x+5,y+h-5), font, 1, (255,255,0), 1)  
        try:
            cv2.imshow('camera_'+ip,frame_flip) 
        except:
            pass
        k = cv2.waitKey(10) & 0xff
        if k == 27:
            cv2.destroyAllWindows()
            break

    print("\n [INFO] Exiting Program and cleanup stuff")
    cv2.destroyAllWindows()


def video_recognize(request, service_api_key, owner, videoPath, count, namesList):
    response = Face_Collection.objects.none()
    id = count
    names = namesList
    path = './API/' + videoPath
    print(path)
    vidcap = cv2.VideoCapture(path)
    success, img = vidcap.read(1)
    cv2.imwrite("./API/frames/image.jpg", img)
    width = Image.open('./API/frames/image.jpg').width
    height = Image.open('./API/frames/image.jpg').height

    # while width > 1280 or height > 720:
    #     width /= 2
    #     height /= 2

    minW = 0.1*width
    minH = 0.1*height

    while success:
        # image = cv2.resize(img,(int(800),int(600)))
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
            face_img = img[y:y + h, x:x + w]
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
                        obj = save(request, service_api_key, owner, now, face_img, id)
                        response |= Face_Collection.objects.filter(id=obj.id)
                except Exception:
                        obj = save(request, service_api_key, owner, now, face_img, id)
                        response |= Face_Collection.objects.filter(id=obj.id)
                
            else:
                id = "unknown"
                confidence = "  {0}%".format(round(100 - confidence))
                now = datetime.now(utc) 
                try:
                    person = Face_Collection.objects.latest('id')
                    last_detection = person.created_at
                    difference = now - last_detection
                    if difference.seconds > 60 or id != person.name:
                        obj = save(request, service_api_key, owner, now, face_img, id)
                        response |= Face_Collection.objects.filter(id=obj.id)
                except Exception:
                        obj = save(request, service_api_key, owner, now, face_img, id)
                        response |= Face_Collection.objects.filter(id=obj.id)
            
            cv2.putText(img, str(id), (x+5,y-5), font, 1, (255,255,255), 2)
            cv2.putText(img, str(confidence), (x+5,y+h-5), font, 1, (255,255,0), 1)  
            detected_photo = img

        try:
            cv2.imshow('Video recognition service',img)  
        except:
            pass
        
        success, img = vidcap.read()
        k = cv2.waitKey(10) & 0xff
        if k == 27:
            vidcap.release()
            cv2.destroyAllWindows()
            if response:
                current_time = now.strftime("%d_%m_%Y_%H_%M_%S")
                path = './API/detected/det.%s.png' % current_time
                cv2.imwrite(path, detected_photo)
                return path, response
            return None, None

    print("\n [INFO] Exiting Program and cleanup stuff")
    vidcap.release()
    cv2.destroyAllWindows()
    if response:
        current_time = now.strftime("%d_%m_%Y_%H_%M_%S")
        path = './API/detected/det.%s.png' % current_time
        cv2.imwrite(path, detected_photo)
        return path, response
    return None, None

