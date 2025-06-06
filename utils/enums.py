from enum import Enum

class ResponseCode(Enum):
    SUCCESS = (200, "操作成功")
    
    BAD_REQUEST = (400, "请求参数错误")
    UNAUTHORIZED = (401, "未授权")
    FORBIDDEN = (403, "禁止访问")
    NOT_FOUND = (404, "资源不存在")
    METHOD_NOT_ALLOWED = (405, "方法不允许")
    
    INTERNAL_ERROR = (500, "服务器内部错误")
    SERVICE_UNAVAILABLE = (503, "服务不可用")
    
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg
