import json
import os
import shutil
import time
import uuid
from django.core import serializers as ser
from unicodedata import name
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.forms import model_to_dict
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from API.serializers import *
from Face_Service import settings
from . import face_dataset, face_recognition, face_training
from .camera import PcCamera , IPWebCam
from .models import *
import threading
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework_xml.renderers import XMLRenderer
from dicttoxml import dicttoxml
try:
    from shlex import quote
except ImportError:  # py2
    from pipes import quote



######################### Global variables #########################
pc_camera = None
webcam_cameras = []
webcam_cameras_ips = []
#####################################################################

######################### Functions #########################
def to_curl(request, compressed=False, verify=True):
    """
    Returns string with curl command by provided request object

    Parameters
    ----------
    compressed : bool
        If `True` then `--compressed` argument will be added to result
    """
    parts = [
        ('curl', None),
        ('-X', request.method),
    ]
    parts += [(None, request.path)]
    for k, v in sorted(request.FILES.items()):
        parts += [('-F', '{0}: {1}'.format(k, v))]
 

    flat_parts = []
    for k, v in parts:
        if k:
            flat_parts.append(quote(k))
        if v:
            flat_parts.append(quote(v))

    return ' '.join(flat_parts) 
def getMyProfile(request):
  try:
    profile = Profile.objects.get(owner = request.user)
  except Profile.DoesNotExist:
    return None
  return profile

def getNamesList(people):
  names = ['']
  for person in people:
    if person.id == len(names):
      names.append(person.name)
    else:
      names.append('')
  return names

def video_clear():
  Video.objects.filter().delete()
  folder_location = './API/videos'
  shutil.rmtree(folder_location, ignore_errors = True)

def getWebcamObjectId(ip):
  index = 0
  for cip in webcam_cameras_ips:
    if cip == ip:
      return index
    index += 1
  return -1

def gen(camera):
  while True:
    try:
      if camera.getExitFlag() == True:
        break
      if camera.getFlag() == False:
        time.sleep(2)
    except Exception:
      pass
    try:
      frame = camera.get_frame()
      yield (b'--frame\r\n'
          b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
    except Exception:
      print('Reconnecting...')
      time.sleep(2)

def personClear(id):
  person = Person.objects.get(id = id)
  count = 1
  while count <= 50:
    photo_location = "./API/dataset/User." + str(id) + '.' + str(count) + ".jpg"
    try:
      os.remove(photo_location)
    except:
      pass
    count += 1
  for photo in person.photos.all():
    photo.delete()
  person.delete()

def detectedpersonClear(id):
  person = Face_Collection.objects.get(id = id)
  try:
    print(person.path)
    os.remove(str(person.path))
  except:
    print('Image not found!')
  person.delete()

def detectedPeopleClear(people):
  try:
    shutil.rmtree('./API/Face_Collection', ignore_errors = True)
  except:
    print('Images not found!')

  directory = "Face_Collection"
  parent_dir = "./API/"
  path = os.path.join(parent_dir, directory)
  os.mkdir(path)
  people.delete()

def detectedPhotosClear():
  try:
    shutil.rmtree('./API/detected', ignore_errors = True)
  except:
    print('Image not found!')
  directory = "detected"
  parent_dir = "./API/"
  path = os.path.join(parent_dir, directory)
  os.mkdir(path)
  
  
#####################################################################


######################### Views #########################
def toHome(request):
  detectedPhotosClear()
  if request.user.username == "admin":
        logout(request)
  if request.user.is_authenticated:
    profile = getMyProfile(request)
    services = Services.objects.filter(owner = profile)
    live_services = Services.objects.filter(owner = profile, type = "Face recognition live", status = True)
    flag = 0

    # Background recognition
    global webcam_cameras, webcam_cameras_ips
    webcam_cameras = []
    webcam_cameras_ips = []
    for service in live_services:
      if service.live_type == False and flag == 0:
        global pc_camera
        if pc_camera is None:
          pc_camera = PcCamera(profile.id, request,service.api_key)
        t = threading.Thread(target=background_pc_recognition)
        t.setDaemon(True)
        t.start()
        flag = 1
      else:
        webcam_cameras.append(IPWebCam(service.socket_ip,profile.id,request, service.api_key))
        webcam_cameras_ips.append(service.socket_ip)
        t = threading.Thread(target=background_webcam_recognition, args=[service.socket_ip])
        t.setDaemon(True)
        t.start()


    return render(request , 'Home.html',{
    'myProfile':profile,
    'services':services,
    'live_services':live_services
    })

  return redirect('login')

def signup(request):
  if request.user.is_authenticated:
    request.session.set_expiry(5000)
    return redirect('Home')

  if request.method == "POST":
    fname = request.POST['fname']
    lname = request.POST['lname']
    email = request.POST['email']
    pass1 = request.POST['pswd1']
    pass2 = request.POST['pswd2']

    if User.objects.filter(email=email):
      messages.error(request,"Email is already exist!")
      return redirect('signup')

    elif len(pass1)<8:
      messages.error(request,"Password must be at least 8 characters!")
      return redirect('signup')

    elif pass1 != pass2:
      messages.error(request, "passwoed didn't match!")
      return redirect('signup')

    else:
       my_user = User.objects.create_user(email,email,pass1)
       my_user.first_name = fname
       my_user.last_name = lname
       my_user.is_active = True
       my_user.save()

       new_profile = Profile(title = fname+' '+lname,owner = my_user)
       new_profile.save()
       
       messages.success(request, "Account created successfully")
       
       return redirect('login')
    

  return render(request, "auth/signup.html")      


def log_in(request):
   if request.user.is_authenticated:
    return redirect('Home')
   if request.method == "POST":
      email = request.POST['email']
      password = request.POST['password']

      user = authenticate(username=email, password=password)
      if user is not None:
        login(request, user)
        return redirect('Home')

      messages.error(request, "Incorrect information!")
      return redirect('login')
      
   return render(request, "auth/login.html")      

    

def signout(request):
    logout(request)
    return redirect('Home')

@api_view(['GET','POST'])
@renderer_classes([TemplateHTMLRenderer, XMLRenderer])
def toFC(request):
  detectedPhotosClear()
  if request.user.is_authenticated:
    profile = Profile.objects.get(owner = request.user)
    live_services = Services.objects.filter(owner = profile, type = "Face recognition live", status = True)
    face_collection = Face_Collection.objects.filter(owner = profile)
    serializer = Face_CollectionSerializer(face_collection, many=True)
    data_xml = dicttoxml(serializer.data, custom_root='root', attr_type=False)

    if request.accepted_renderer.format == 'html':
      data = {
        'myProfile':profile,
        'live_services':live_services,
        'face_collection':face_collection,
        'req':to_curl(request),
        'resX':data_xml
      }
      return Response(data , template_name='Face_Collection.html')
    return Response(serializer.data)
  return redirect('login')

def addService(request):
  if request.user.is_authenticated:
    profile = getMyProfile(request)
    if request.method == "POST":
      name = request.POST['name']
      type = request.POST['type']
      live_type = request.POST['live_type']
      socket_ip = request.POST['socket_ip']

      api_key = uuid.uuid4().hex[:24].upper()

      if type == "1":
        type = "Face recognition live"
      else:
        type = "Face recognition video"

      if live_type == "0":
        live_type_value = False
      else:
        live_type_value = True

      new_service = Services(owner = profile,name = name,socket_ip = socket_ip, type = type,live_type = live_type_value, api_key = api_key)
      new_service.save()

    return redirect('Home')
  return redirect('login')

def deleteService(request, sid):
  if request.user.is_authenticated:
    try:
      profile = Profile.objects.get(owner = request.user)
      service = Services.objects.get(id = sid)
    except Services.DoesNotExist or Profile.DoesNotExist:
      return redirect('Home')
    if service.owner == profile:
      service.delete()
  return redirect('Home')



def remove_person(request, pid):
  detectedPhotosClear()
  if request.user.is_authenticated:
    profile = getMyProfile(request)
    try:
      person = Person.objects.get(id = pid, owner = profile)
    except Person.DoesNotExist:
      messages.error(request, "Something went wrong!")
      return redirect('Home')
    personClear(person.id)
    if Person.objects.filter().count() > 0:
      face_training.train()
    return redirect('toPeople')
  return redirect('login')

def remove_detected_person(request, pid):
  detectedPhotosClear()
  if request.user.is_authenticated:
    profile = getMyProfile(request)
    try:
      person = Face_Collection.objects.get(id = pid)
    except Face_Collection.DoesNotExist:
      messages.error(request, "Something went wrong!")
      return redirect('Home')
    detectedpersonClear(person.id)
    return redirect('Face_Collection')
  return redirect('login')

def clear(request):
  detectedPhotosClear()
  if request.user.is_authenticated:
    profile = getMyProfile(request)
    people = Face_Collection.objects.filter(owner = profile)
    detectedPeopleClear(people)
    return redirect('Face_Collection')
  return redirect('login')

def change_ip(request, sid):
  if request.user.is_authenticated:
    if request.method == "POST":
      socket_ip = request.POST['socket_ip']
      if Services.objects.filter(socket_ip = socket_ip).exists():
        messages.error(request, "There are already service with this IP!")
      else:
        service = Services.objects.get(id = sid)
        service.socket_ip = socket_ip
        service.save()
    return redirect('Home')
  return redirect('login')

def toPeople(request):
  detectedPhotosClear()
  if request.user.is_authenticated:
    profile = getMyProfile(request)
    people = Person.objects.filter(owner = profile)
    live_services = Services.objects.filter(owner = profile, type = "Face recognition live", status = True)
    return render(request, "People.html",{
      'people':people,
      'myProfile':profile,
      'live_services':live_services
    })
  return redirect('login')

def trainData(request):
  detectedPhotosClear()
  if request.user.is_authenticated:
    profile = getMyProfile(request)
    services = Services.objects.filter(owner = profile)
    live_services = Services.objects.filter(owner = profile, type = "Face recognition live", status = True)
    if request.method == "POST":
      name = request.POST['name']
      live_type = request.POST['live_type']
      try:
        sip = request.POST['sip']
      except Exception:
        pass

      
      if not Person.objects.filter(name = name).exists():
        id = Person.objects.filter().count() + 1
        new_person = Person(id = id,name = name, owner = profile)
        new_person.save()

        id = new_person.id
        try:
          if live_type == "0":
            if pc_camera is not None:
              res = face_dataset.cam_run(id, pc_camera.video)
            else:
              res = face_dataset.cam_run(id)
          else:
            res = face_dataset.external_cam_run(id,sip)
          if res == False:
              personClear(new_person.id)
              messages.error(request, "Train process was canceled by user!")
              return redirect('train_data')
          try:
            face_training.train()
          except Exception:
            print('Training error!')
          count = 0
          while count <= 50:
            new_photo = PersonPhotos(path = "./API/dataset/User." + str(id) + '.' + str(count) + ".jpg")
            new_photo.save()
            new_person.photos.add(new_photo)
            count += 1
        except Exception as e:
          personClear(new_person.id)
          messages.error(request, "Something went wrong while training!")
          return redirect('train_data')

        
        messages.success(request, "The data trained successfully.")
        return redirect('train_data')
      else:
        messages.error(request, "The user name already in the system.")
        return redirect('train_data')

    cam_services = Services.objects.filter(owner = profile,live_type = True ,type = "Face recognition live", status = True)  
    return render(request, "Train_Data.html",{
        'services':services,
        'live_services':live_services,
        'myProfile':profile,
        'cam_services':cam_services
      })
  return redirect('login')

def run_service(request, sid):
  if request.user.is_authenticated:
    profile = getMyProfile(request)
    service = Services.objects.get(id = sid)
    if service.owner == profile :
      if service.type == "Face recognition video" and Services.objects.filter(owner = profile, status = True, type = "Face recognition video").count() > 0:
        messages.error(request, "Can't run more than one video recognition service!")
      else:
        service.status = True
        service.save()
        if service.type == "Face recognition video":
          return redirect('video_recognition')
    return redirect('Home')

  return redirect('login')


def stop_service(request, sid):
  if request.user.is_authenticated:
    profile = getMyProfile(request)
    service = Services.objects.get(id = sid)
    if service.owner == profile:
      service.status = False
      service.save()
      if service.type == "Face recognition live":
        if service.live_type:
          global webcam_cameras,webcam_cameras_ips
          id = getWebcamObjectId(service.socket_ip)
          if id != -1:
            obj = webcam_cameras[id]
            try:
              obj.release()
            except:
              pass
            del obj
            webcam_cameras_ips.remove(service.socket_ip)
        elif Services.objects.filter(owner = profile, type = "Face recognition live", live_type = False, status = True).count() <= 0:
          global pc_camera
          try:
            pc_camera.release()
          except:
            pass
          del pc_camera
          pc_camera = None

    return redirect('Home')

  return redirect('login')
    
def video_recognition(request):
  detectedPhotosClear()
  if request.user.is_authenticated:
    profile = getMyProfile(request)
    services = Services.objects.filter(owner = profile)
    live_services = Services.objects.filter(owner = profile, type = "Face recognition live", status = True)
    if Services.objects.filter(owner = profile, type = "Face recognition video", status = True).exists():
      service = Services.objects.get(owner = profile, type = "Face recognition video", status = True)
      return render(request, 'Test.html',{
        'myProfile':profile,
        'service':service,
        'services':services,
        'live_services':live_services
      })
    else:
      messages.error(request, "You must run a video recognition service first!")
      return redirect('Home') 

  return redirect('login') 

@api_view(['GET'])
def get_service(request, api_key):
  try:
    service = Services.objects.get(api_key = api_key)
  except Services.DoesNotExist:
    return Response({'Valid': None})
  serializer = ServicesSerializer(service, many = False)
  return Response(serializer.data)

@api_view(['GET'])
def get_services(request, pid):
  profile = Profile.objects.get(id = pid)
  try:
    services = Services.objects.filter(owner = profile)
  except Services.DoesNotExist:
    return Response({'Valid': None})
  serializer = ServicesSerializer(services, many = True)
  return Response(serializer.data)

@api_view(['GET'])
def get_service_faces(request, api_key):
  try:
    faces = Face_Collection.objects.filter(api_key = api_key)
  except Services.DoesNotExist:
    return Response({'Valid': None})
  serializer = Face_CollectionSerializer(faces, many = True)
  return Response(serializer.data)

@api_view(['GET'])
def get_face(request, fid):
  try:
    face = Face_Collection.objects.get(id = fid)
  except Face_Collection.DoesNotExist:
    return Response({'Valid': None})
  serializer = Face_CollectionSerializer(face, many = False)
  return Response(serializer.data)



@api_view(['GET','POST'])
@renderer_classes([TemplateHTMLRenderer, XMLRenderer])
def video_recognition_test(request):
  detectedPhotosClear()
  if request.user.is_authenticated:
    profile = getMyProfile(request)
    services = Services.objects.filter(owner = profile)
    live_services = Services.objects.filter(owner = profile, type = "Face recognition live", status = True)
    try:
      service = Services.objects.get(api_key = request.POST['api_key'])
    except Services.DoesNotExist:
      messages.error(request, 'Service not found!')
      return redirect('video_recognition')
    file = request.FILES.get('file')
    video_clear()
    new_file = Video(path = file)
    new_file.save()
    people = Person.objects.filter()
    count = people.count() - 1
    names = getNamesList(people)
    if not file:
      return redirect('video_recognition')
    # try:
    image_path, queryset = face_recognition.video_recognize(request, service.api_key, profile,str(new_file.path),count,names)
    # except Exception:
    #   messages.error(request, "Something went wrong!")
    #   video_clear()
    #   return redirect('video_recognition')
    if queryset is None:
      messages.error(request, "Nothing detected!")
      video_clear()
      return redirect('video_recognition')
    if request.accepted_renderer.format == 'html':
        serializer = Face_CollectionSerializer(queryset, many=True)
        ser_xml = dicttoxml(serializer.data, custom_root='root', attr_type=False)
        data = {
          'myProfile': profile,
          'service': service,
          'resx': ser_xml,
          'img': image_path,
          'req': to_curl(request),
          'services':services,
          'live_services':live_services
        }
        return Response(data, template_name='Result.html')

    serializer = Face_CollectionSerializer(queryset, many=True)
    data = serializer.data
    return Response(data)

  return redirect('login')

#####################################################################


######################### Background section ########################
def background_pc_recognition():
  people = Person.objects.filter()
  count = people.count() - 1
  names = getNamesList(people)
  pc_camera.live(count, names)

def background_webcam_recognition(ip):
  people = Person.objects.filter()
  count = people.count() - 1
  names = getNamesList(people)
  id = getWebcamObjectId(ip)
  if id != -1:
    webcam_cameras[id].live(count, names)


def pccam_stream(request):
  return StreamingHttpResponse(gen(pc_camera),
          content_type='multipart/x-mixed-replace; boundary=frame')


def webcam_stream(request, camera_ip):
  id = getWebcamObjectId(camera_ip) 
  return StreamingHttpResponse(gen(webcam_cameras[id]),
          content_type='multipart/x-mixed-replace; boundary=frame')
#####################################################################