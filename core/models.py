from django.db import models
from django.urls import reverse


from django.db import models

class MediaCategory(models.Model):
    name = models.CharField(max_length=100)
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Media Categories"
        ordering = ['order']

    def __str__(self):
        return self.name

class MediaItem(models.Model):
    category = models.ForeignKey(MediaCategory, on_delete=models.CASCADE, related_name='media_items')
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='media_recognition/')
    link = models.URLField(max_length=500, blank=True, null=True)
    is_highlighted = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Media Items"
        ordering = ['order']

    def __str__(self):
        return self.title
    
    from django.db import models

class CallbackRequest(models.Model):
    name = models.CharField(max_length=255)
    mobile_no = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.subject}"
