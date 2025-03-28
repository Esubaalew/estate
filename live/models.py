from django.db import models

class Request(models.Model):
    user_id = models.CharField(max_length=255)
    username = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    address = models.TextField()
    additional_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_responded = models.BooleanField(default=False)

    def __str__(self):
        return f"Request from {self.name} (User ID: {self.user_id})"


class Message(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE)
    sender_id = models.CharField(max_length=255)
    admin_id = models.CharField(max_length=255, default='1648265210')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender_id} on {self.created_at}"
