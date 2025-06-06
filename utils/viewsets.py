from rest_framework import viewsets
from utils.response import APIResponse
from utils.enums import ResponseCode

class CustomModelViewSet(viewsets.ModelViewSet):
    """
    自定义视图集基类，统一处理响应格式，使用ResponseCode枚举管理响应状态
    """
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse(
            response_code=ResponseCode.SUCCESS,
            data={"list": serializer.data, "total": len(serializer.data)}
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse(response_code=ResponseCode.BAD_REQUEST, data=serializer.errors)
        try:
            self.perform_create(serializer)
            return APIResponse(response_code=ResponseCode.SUCCESS, data=serializer.data)
        except Exception as e:
            return APIResponse(response_code=ResponseCode.INTERNAL_ERROR, data=str(e))

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse(data=serializer.data)
        except Exception as e:
            return APIResponse(response_code=ResponseCode.NOT_FOUND, data=str(e))

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            if not serializer.is_valid():
                return APIResponse(response_code=ResponseCode.BAD_REQUEST, data=serializer.errors)
            self.perform_update(serializer)
            return APIResponse(response_code=ResponseCode.SUCCESS, data=serializer.data)
        except Exception as e:
            return APIResponse(response_code=ResponseCode.INTERNAL_ERROR, data=str(e))

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return APIResponse(response_code=ResponseCode.SUCCESS)
        except Exception as e:
            return APIResponse(response_code=ResponseCode.INTERNAL_ERROR, data=str(e))