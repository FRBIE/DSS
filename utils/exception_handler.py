from rest_framework.views import exception_handler
from utils.response import APIResponse
from utils.enums import ResponseCode
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    自定义异常处理器，处理不同类型的异常并返回统一的响应格式
    :param exc: 异常对象
    :param context: 异常上下文
    :return: Response对象
    """
    # 记录异常信息
    logger.error(f"异常类型: {type(exc).__name__}")
    logger.error(f"异常信息: {str(exc)}")
    logger.error(f"异常上下文: {context}")

    # 处理分页相关异常
    if "Page" in str(exc):
        return APIResponse(
            response_code=ResponseCode.NOT_FOUND,
            data={"detail": str(exc)}
        )

    # 获取原始的DRF异常响应
    response = exception_handler(exc, context)
    
    if response is not None:
        status_code = response.status_code
        response_code = None
        
        if status_code == 400:
            response_code = ResponseCode.BAD_REQUEST
        elif status_code == 401:
            response_code = ResponseCode.UNAUTHORIZED
        elif status_code == 403:
            response_code = ResponseCode.FORBIDDEN
        elif status_code == 404:
            response_code = ResponseCode.NOT_FOUND
        elif status_code == 405:
            response_code = ResponseCode.METHOD_NOT_ALLOWED
        else:
            response_code = ResponseCode.BAD_REQUEST

        # 只返回响应码和数据，避免重复的消息
        return APIResponse(
            response_code=response_code,
            data=response.data
        )
    
    # 处理未捕获的异常
    error_detail = str(exc) if str(exc) else "服务器内部错误"
    logger.error(f"未处理的异常: {error_detail}", exc_info=True)
    
    return APIResponse(
        response_code=ResponseCode.INTERNAL_ERROR,
        data={"detail": error_detail}
    )
