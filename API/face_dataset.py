import cv2
import urllib.request

import numpy as np

def external_cam_run(id, sip):
    url = "http://"+sip+"/shot.jpg"

    face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml");
    # For each person, enter one numeric face id (must enter number start from 1, this is the lable of person 1)
    face_id = id
    
    print("\n [INFO] Initializing face capture. Look the external camera and wait ...")
    # Initialize individual sampling face count
    count = 0
    # We are using Motion JPEG, but OpenCV defaults to capture raw images,
    # so we must encode it into JPEG in order to correctly display the
    # video stream

    while(True):
        imgResp = urllib.request.urlopen(url)
        imgNp = np.array(bytearray(imgResp.read()),dtype=np.uint8)
        img= cv2.imdecode(imgNp,-1)    
        resize = cv2.resize(img, (640, 480), interpolation = cv2.INTER_LINEAR) 
        frame_flip = cv2.flip(resize,1)

        gray = cv2.cvtColor(frame_flip, cv2.COLOR_BGR2GRAY)

        faces = face_detector.detectMultiScale(gray, 1.3, 5)
        for (x,y,w,h) in faces:
            cv2.rectangle(frame_flip, (x,y), (x+w,y+h), (255,0,0), 2)     
            count += 1
            
            # Save the captured image into the datasets folder
            cv2.imwrite("./API/dataset/User." + str(face_id) + '.' + str(count) + ".jpg", gray[y:y+h,x:x+w])


        cv2.imshow('External-Camera Training', frame_flip)

        k = cv2.waitKey(100) & 0xff # Press 'ESC' for exiting video
        if k == 27:
            return False
        elif count >= 50: # Take 50 face sample and stop video
            break

    # Do a bit of cleanup
    print("\n [INFO] Exiting Program and cleanup stuff")
    cv2.destroyAllWindows()
    return True
    


def cam_run(id, cam = None):
    flag = False
    print(cam)
    if cam == None:
        cam = cv2.VideoCapture(0)
        cam.set(3, 640) # set video width
        cam.set(4, 480) # set video height
        flag = True

    #make sure 'haarcascade_frontalface_default.xml' is in the same folder as this code
    face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml");

    # For each person, enter one numeric face id (must enter number start from 1, this is the lable of person 1)
    face_id = id
    
    print("\n [INFO] Initializing face capture. Look the camera and wait ...")
    # Initialize individual sampling face count
    count = 0
    #start detect your face and take 30 pictures
    while(True):
        ret, img = cam.read()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_detector.detectMultiScale(gray, 1.3, 5)
        for (x,y,w,h) in faces:
            cv2.rectangle(img, (x,y), (x+w,y+h), (255,0,0), 2)     
            count += 1
            
            # Save the captured image into the datasets folder
            cv2.imwrite("./API/dataset/User." + str(face_id) + '.' + str(count) + ".jpg", gray[y:y+h,x:x+w])


        cv2.imshow('PC Training', img)

        k = cv2.waitKey(100) & 0xff # Press 'ESC' for exiting video
        if k == 27:
            if flag:
                cam.release()
            cv2.destroyAllWindows()
            return False
        elif count >= 50: # Take 50 face sample and stop video
            break

    # Do a bit of cleanup
    print("\n [INFO] Exiting Program and cleanup stuff")
    if flag:
        cam.release()
    cv2.destroyAllWindows()
    return True



