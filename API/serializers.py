from rest_framework import serializers
from API.models import *


class Face_CollectionSerializer(serializers.ModelSerializer):
 class Meta:
    model = Face_Collection
    fields = ['id', 'name', 'path','created_at','api_key']

class ServicesSerializer(serializers.ModelSerializer):
 class Meta:
    model = Services
    fields = '__all__'
    