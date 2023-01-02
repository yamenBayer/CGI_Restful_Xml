from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    title = models.CharField(max_length=100)
    owner = models.OneToOneField(User, related_name='owner' , on_delete= models.CASCADE)
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Services(models.Model):
    owner = models.ForeignKey(Profile, related_name='service_owner' , on_delete= models.CASCADE)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    api_key = models.CharField(max_length=100, unique = True)
    status = models.BooleanField(default = False)
    socket_ip = models.CharField(max_length=100, blank=True)
    live_type = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class PersonPhotos(models.Model):
    path = models.ImageField(default='API/dataset/')


class Person(models.Model):
    owner = models.ForeignKey(Profile, related_name='person_owner' , on_delete= models.CASCADE)
    name = models.CharField(max_length=100, unique=True)
    photos = models.ManyToManyField(PersonPhotos, related_name='person_photos')

    def __str__(self):
        return self.name

class Video(models.Model):
    path = models.FileField(upload_to='videos/')


class Face_Collection(models.Model):
    owner = models.ForeignKey(Profile, related_name='face_collection_owner' , on_delete= models.CASCADE)
    name = models.CharField(max_length=100)
    path = models.ImageField(default='API/Face_Collection/')
    created_at = models.DateTimeField(auto_now_add=True)
    api_key = models.CharField(max_length=100)
    request = models.CharField(max_length=100, blank=True, null=True)
    restful_response_json = models.CharField(max_length=100, blank=True, null=True)
    restful_response_xml = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name + ' | ' + str(self.created_at.date()) + ' | ' + str(self.created_at.hour) + ':' + str(self.created_at.minute)