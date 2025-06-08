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
    def get(self, request):
        active = request.GET.get('active', '0')  # Always string from GET
        yolo = YoloController()
        
        try:
            if active == '1':
                data = yolo.get_active_categories()
                data = [i.categories for i in data]
            else:
                data = list(yolo.get_all_categories().values())  # or simply: list(yolo.get_all_categories())
        except Exception as e:
            return Response({'error': str(e)}, status=500)

        return Response({'categories': data}, status=200)

    def post(self,request):
        categories=request.data.get('categories')
        yolo=YoloController()
        yolo.post_new_categories(categories=categories)
        return Response(data='Updated the categories',status=200)