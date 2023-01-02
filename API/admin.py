from django.contrib import admin
from .models import Profile,Services,Person, Video,PersonPhotos, Face_Collection

admin.site.register(Profile)
admin.site.register(Services)
admin.site.register(Person)
admin.site.register(Video)
admin.site.register(PersonPhotos)
admin.site.register(Face_Collection)