from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Message, Request

@receiver(post_save, sender=Message)
def mark_request_as_responded(sender, instance, created, **kwargs):
    if created:
        request_instance = instance.request
        request_instance.is_responded = True
        request_instance.save()

        clean_up_old_requests()

@receiver(post_save, sender=Request)
def delete_old_requests(sender, instance, created, **kwargs):
    if created:
        Request.objects.filter(user_id=instance.user_id).exclude(id=instance.id).delete()

        clean_up_old_requests()


def clean_up_old_requests():
    now = timezone.now()

    three_hours_ago = now - timedelta(hours=3)
    Request.objects.filter(is_responded=True, created_at__lt=three_hours_ago).delete()


    thirty_minutes_ago = now - timedelta(minutes=30)
    Request.objects.filter(is_responded=False, created_at__lt=thirty_minutes_ago).delete()