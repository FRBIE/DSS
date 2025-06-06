from rest_framework.response import Response
from rest_framework import status
from .enums import ResponseCode

class APIResponse(Response):
    def __init__(self, response_code=ResponseCode.SUCCESS, data=None, status=status.HTTP_200_OK, **kwargs):
        """
        统一的API响应格式
        :param response_code: ResponseCode枚举类型，包含code和msg
        :param data: 响应数据
        :param status: HTTP状态码，默认200
        :param kwargs: 其他参数
        """
        if not isinstance(response_code, ResponseCode):
            response_code = ResponseCode.SUCCESS
            
        resp_data = {
            'code': response_code.code,
            'msg': response_code.msg,
            'data': data
        }
        resp_data.update(kwargs)
        super().__init__(data=resp_data, status=status)
