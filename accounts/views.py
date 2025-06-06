from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema

from .serializers import UserSerializer, LoginSerializer
from rest_framework.authentication import SessionAuthentication

class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return  # To not perform the csrf check previously happening
class RegisterView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=UserSerializer,  # 显式关联序列化器
        operation_description="注册新用户",
        responses={201: UserSerializer, 400: "无效数据"}
    )
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': serializer.data,
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)

    permission_classes = [AllowAny]
    @swagger_auto_schema(
        request_body=LoginSerializer,  # 直接使用序列化器（推荐）
        operation_description="用户登录",
    )
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        # 参数检查（业务码400）
        if not username or not password:
            return Response({
                "code": 400,  # 自定义业务码
                "msg": "用户名和密码不能为空",
                "data": {}
            })  # HTTP状态码仍然是200

        # 认证逻辑（业务码401）
        user = authenticate(username=username, password=password)
        if not user:
            return Response({
                "code": 401,  # 自定义业务码
                "msg": "用户名或密码错误",
                "data": {}
            })  # HTTP状态码仍然是200

        # 成功（业务码200）
        refresh = RefreshToken.for_user(user)
        return Response({
            "code": 200,
            "msg": "登录成功",
            "data": {
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }
        })