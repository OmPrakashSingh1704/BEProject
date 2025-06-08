from rest_framework.response import Response
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from .yolofns import YoloController,StreamWrapper

class WebcamStreamView(APIView):
    """
    Stream webcam feed as multipart/x-mixed-replace response.
    """

    def get(self, request, *args, **kwargs):
        yolo = YoloController(feed=0)
        stream = StreamWrapper(yolo)
        response = StreamingHttpResponse(stream, content_type='multipart/x-mixed-replace; boundary=frame')
        response._resource_closers.append(stream.close)
        return response
class Categories(APIView):
    def get(self,request):
        active=request.GET.get('active',0)
        yolo=YoloController()
        if active:return Response(data=yolo.get_active_categories(),status=200)
        else:return Response(data=yolo.get_all_categories(),status=200)

    def post(self,request):
        categories=request.data.get('categories')
        yolo=YoloController()
        yolo.post_new_categories(categories=categories)
        return Response(data='Updated the categories',status=200)