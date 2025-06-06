from rest_framework.views import exception_handler
from utils.response import APIResponse
from utils.enums import ResponseCode

def custom_exception_handler(exc, context):
    """
    自定义异常处理器
    :param exc: 异常对象
    :param context: 异常上下文
    :return: Response对象
    """
    # 先调用REST framework默认的异常处理
    response = exception_handler(exc, context)
    
    if response is None:
        # 如果是未处理的异常,返回500错误
        return APIResponse(
            response_code=ResponseCode.INTERNAL_ERROR,
            data=None
        )
        
    return response
