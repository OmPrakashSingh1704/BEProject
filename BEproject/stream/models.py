from django.db import models

# Create your models here.
class YoloClassifier(models.Model):
    categories=models.TextField(null=True)
    
    def __str__(self):
        return self.categories
    
    def __repr__(self):
        return self.categories