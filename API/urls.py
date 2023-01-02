from . import views
from django.urls import path

urlpatterns = [
    
    # site urls
    path('', views.toHome, name="Home"),
    path('login', views.log_in, name="login"),
    path('signup', views.signup, name="signup"),
    path('signout', views.signout, name="signout"),
    path('train_data', views.trainData, name="train_data"),   
    path('people', views.toPeople, name="toPeople"),    
    path('add_service', views.addService, name="add_service"),    
    path('change_ip/<sid>', views.change_ip, name="change_ip"),    
    path('remove_service/<sid>', views.deleteService, name="remove_service"),    
    path('remove_person/<pid>', views.remove_person, name="remove_person"),    
    path('remove_detected_person/<pid>', views.remove_detected_person, name="remove_detected_person"),    
    path('clear', views.clear, name="clear"),    
    path('test', views.video_recognition, name="video_recognition"),    
    path('run_service/<sid>', views.run_service, name="run_service"),    
    path('stop_service/<sid>', views.stop_service, name="stop_service"),  

    # video stream urls
    path('pccam_stream', views.pccam_stream, name='pccam_stream'),
    path('webcam_stream/<camera_ip>', views.webcam_stream, name='webcam_stream'),
    
    # Restful API
    path('api/service/<str:api_key>', views.get_service),
    path('api/services/<str:pid>', views.get_services),
    path('api/service/faces/<str:api_key>', views.get_service_faces),
    path('api/face/<str:fid>', views.get_face),

    path('testing', views.video_recognition_test, name="video_recognition_test"),    
    path('collection', views.toFC, name="Face_Collection"),    

]
