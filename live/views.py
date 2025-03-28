from rest_framework import viewsets
from rest_framework.response import Response
from .models import Request, Message
from .serializers import RequestSerializer, MessageSerializer

class RequestViewSet(viewsets.ModelViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer

    def update(self, request, pk):
        # Mark the request as responded
        request_instance = self.get_object()
        request_instance.is_responded = True
        request_instance.save()

        return Response({"status": "Request marked as responded."})

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    def create(self, request):
        # Deserialize and validate the incoming data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract the validated data
        validated_data = serializer.validated_data
        request_instance = validated_data.get('request')
        sender_id = validated_data.get('sender_id')


        if request_instance.user_id == sender_id:

            request_instance.is_responded = True
            request_instance.save()


        serializer.save()

        return Response(serializer.data)
