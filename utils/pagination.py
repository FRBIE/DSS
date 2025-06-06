from rest_framework.pagination import PageNumberPagination
from utils.response import APIResponse
from utils.enums import ResponseCode

class StandardPagination(PageNumberPagination):
    page_size = 10
    page_query_param = 'page'
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def get_paginated_response(self, data):
        return APIResponse(
            response_code=ResponseCode.SUCCESS,
            data={
                "list": data if data is not None else [],
                "total": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.page.paginator.per_page
            }
        )