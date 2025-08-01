from utils.viewsets import CustomModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Prefetch
from rest_framework.viewsets import GenericViewSet
from rest_framework import mixins, status
from django.http import HttpResponse
import csv
import codecs
from .models import Dictionary, DataTemplate, Archive, Case, Identity, DataTable, DataTemplateCategory
from .serializers import (
    DictionarySerializer, DataTemplateSerializer,
    ArchiveListSerializer, ArchiveDetailSerializer, ArchiveSerializer,
    CaseListSerializer, CaseDetailSerializer, CaseSerializer,
    IdentitySerializer, PatientDetailSerializer, DataTableDetailSerializer,
    DataTableSerializer, DataTableBulkCreateSerializer,
    DataTemplateCategorySerializer, DictionaryBulkImportSerializer,
    PatientMergedCaseSerializer, CaseVisualizationOptionSerializer,
    CaseVisualizationDataSerializer, CaseVisualizationDataPointSerializer
)
from utils.pagination import StandardPagination
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import serializers
from datetime import date
from django.utils.dateparse import parse_datetime
from utils.response import APIResponse
from utils.enums import ResponseCode

class DictionaryViewSet(CustomModelViewSet):
    """
    API endpoint for 系统词条 (System Dictionary).

    - 支持通过 word_code 或 id 查询、修改、删除单个词条：
      例如 /api/dictionary/1/ 或 /api/dictionary/ABC123/ 都可以。
      优先按 word_code 查找，查不到且参数为纯数字时自动按 id 查找。

    - **Create**: POST /api/dictionary/
      - `word_code` is auto-generated.
      - Required fields: `word_name`, `word_class`, `word_apply`.
      - Optional fields: `word_eng`, `word_short`, `word_belong`, `data_type`.
    - **List**: GET /api/dictionary/
      - 支持分页: ?page=1&page_size=10
    - **Retrieve**: GET /api/dictionary/{word_code or id}/
    - **Update**: PUT /api/dictionary/{word_code or id}/ (all fields except word_code)
    - **Partial Update**: PATCH /api/dictionary/{word_code or id}/ (specified fields except word_code)
    - **Delete**: DELETE /api/dictionary/{word_code or id}/
    """
    queryset = Dictionary.objects.all().order_by('word_code')
    serializer_class = DictionarySerializer
    lookup_field = 'word_code'
    pagination_class = StandardPagination

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(lookup_url_kwarg)
        queryset = self.get_queryset()
        # 优先按 word_code 查找
        try:
            return queryset.get(word_code=lookup_value)
        except Dictionary.DoesNotExist:
            # 如果是纯数字，尝试按 id 查找
            if str(lookup_value).isdigit():
                try:
                    return queryset.get(id=int(lookup_value))
                except Dictionary.DoesNotExist:
                    pass
        self.does_not_exist()

    def does_not_exist(self):
        from rest_framework.exceptions import NotFound
        raise NotFound('未找到对应的词条（word_code 或 id）')

    @swagger_auto_schema(
        operation_description="""
        创建或更新词条：
        - 如果请求中包含 id 或 word_code，且数据库中存在，则进行更新操作（优先 id，再 word_code，再 word_name）。
        - 如果都没有或都查不到，则创建新词条。
        
        请求体可包含：
        - id（可选，存在则优先用于更新）
        - word_code（可选，存在则用于更新）
        - word_name（可选，存在则用于更新）
        其他字段同词条定义。
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['word_name', 'word_class', 'input_type', 'options'],  # 移除 word_apply
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='词条ID（可选，如果提供且存在则进行更新操作）'),
                'word_code': openapi.Schema(type=openapi.TYPE_STRING, description='词条编号（可选，如果提供且存在则进行更新操作）'),
                'word_name': openapi.Schema(type=openapi.TYPE_STRING, description='中文名称'),
                'word_eng': openapi.Schema(type=openapi.TYPE_STRING, description='英文名称'),
                'word_short': openapi.Schema(type=openapi.TYPE_STRING, description='英文缩写'),
                'word_class': openapi.Schema(type=openapi.TYPE_STRING, description='词条类型'),
                'word_apply': openapi.Schema(type=openapi.TYPE_STRING, description='词条应用（可选）'),
                'word_belong': openapi.Schema(type=openapi.TYPE_STRING, description='从属别名'),
                'data_type': openapi.Schema(type=openapi.TYPE_STRING, description='数据类型'),
                'input_type': openapi.Schema(type=openapi.TYPE_STRING, description='填写方式'),
                'options': openapi.Schema(type=openapi.TYPE_STRING, description='主选项'),
                'followup_options': openapi.Schema(type=openapi.TYPE_OBJECT, description='后续选项'),
                'has_unit': openapi.Schema(type=openapi.TYPE_INTEGER, description='是否有单位 0-无 1-有'),
                'unit': openapi.Schema(type=openapi.TYPE_STRING, description='词条单位'),
                'is_score': openapi.Schema(type=openapi.TYPE_INTEGER, description='是否为评分词条 0-不是 1-是'),
                'score_func': openapi.Schema(type=openapi.TYPE_STRING, description='评分计算方式'),
            },
            example={
                "id": 354,
                "word_code": "A000001",
                "word_name": "抗病毒",
                "word_eng": "",
                "word_short": "",
                "word_class": "临床信息",
                # "word_apply": "临床",  # 可选
                "word_belong": "",
                "data_type": "",
                "input_type": "single",
                "options": "恩替卡韦,替诺福韦,无,其他",
                "followup_options": {},
                "has_unit": 0,
                "unit": "",
                "is_score": 1,
                "score_func": "我是具体的评分计算方式，存储为字符串"
            }
        )
    )
    def create(self, request, *args, **kwargs):
        # 支持通过 id 或 word_code 或 word_name 查找已存在的词条并更新，优先级 id > word_code > word_name
        dictionary_id = request.data.get('id')
        word_code = request.data.get('word_code')
        word_name = request.data.get('word_name')
        instance = None

        # 优先用 id 查找
        if dictionary_id:
            try:
                instance = Dictionary.objects.get(id=dictionary_id)
            except Dictionary.DoesNotExist:
                instance = None

        # 用 word_code 查找
        if not instance and word_code:
            try:
                instance = Dictionary.objects.get(word_code=word_code)
            except Dictionary.DoesNotExist:
                instance = None

        # 用 word_name 查找（兼容原逻辑）
        if not instance and word_name:
            try:
                instance = Dictionary.objects.get(word_name=word_name)
            except Dictionary.DoesNotExist:
                instance = None

        if instance:
            # 更新操作，word_code 不变
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if not serializer.is_valid():
                return APIResponse(response_code=ResponseCode.BAD_REQUEST, data=serializer.errors)
            self.perform_update(serializer)
            return APIResponse(response_code=ResponseCode.SUCCESS, data=serializer.data)
        # 执行原有的创建逻辑
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="查询单个词条（支持 word_code 或 id 作为路径参数）",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="更新单个词条（支持 word_code 或 id 作为路径参数）",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="部分更新单个词条（支持 word_code 或 id 作为路径参数）",
        manual_parameters=[
            openapi.Parameter(
                'word_code',
                openapi.IN_PATH,
                description="词条编号或id（均可作为路径参数）",
                type=openapi.TYPE_STRING,
                required=True
            )
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="删除单个词条（支持 word_code 或 id 作为路径参数）",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="根据 word_name 完全匹配查询词条信息\nGET /api/dictionary/by-word-name/?word_name=xxx",
        manual_parameters=[
            openapi.Parameter(
                'word_name', openapi.IN_QUERY, description="要精确匹配的词条中文名称", type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="查询成功，返回词条信息",
                examples={
                    "application/json": {
                        "code": 200,
                        "msg": "查询成功",
                        "data": {
                            "id": 1,
                            "word_code": "A000001",
                            "word_name": "抗病毒",
                            "word_eng": "",
                            "word_short": "",
                            "word_class": "临床信息",
                            "word_apply": "临床",
                            "word_belong": "",
                            "data_type": "",
                            "input_type": "single",
                            "options": "恩替卡韦,替诺福韦,无,其他",
                            "followup_options": {},
                            "has_unit": 0,
                            "unit": "",
                            "is_score": 1,
                            "score_func": "我是具体的评分计算方式，存储为字符串"
                        }
                    }
                }
            ),
            400: '缺少 word_name 参数',
            404: '未找到对应词条'
        }
    )
    @action(detail=False, methods=['get'], url_path='by-word-name')
    def search_by_word_name(self, request):
        """
        根据 word_name 完全匹配查询词条信息
        GET /api/dictionary/by-word-name/?word_name=xxx
        """
        word_name = request.query_params.get('word_name')
        if not word_name:
            return Response({
                'code': 400,
                'msg': '请提供 word_name 参数',
                'data': None
            }, status=400)
        try:
            instance = Dictionary.objects.get(word_name=word_name)
        except Dictionary.DoesNotExist:
            return Response({
                'code': 404,
                'msg': f'未找到 word_name 为 {word_name} 的词条',
                'data': None
            }, status=404)
        serializer = self.get_serializer(instance)
        return Response({
            'code': 200,
            'msg': '查询成功',
            'data': serializer.data
        })

    def list(self, request, *args, **kwargs):
        """
        如果不传 page 和 page_size，则返回全部词条（不分页）。否则按分页参数返回。
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = request.query_params.get('page')
        page_size = request.query_params.get('page_size')
        if page is None and page_size is None:
            # 不分页，返回全部
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'code': 200,
                'msg': '查询成功',
                'data': {
                    'list': serializer.data,
                    'total': len(serializer.data),
                    'page': 1,
                    'page_size': len(serializer.data)
                }
            })
        # 否则走原有分页逻辑
        return super().list(request, *args, **kwargs)

class DataTemplateViewSet(CustomModelViewSet):
    """
    API endpoint for 临床模板管理.

    - **Create**: POST /api/data-template/
      - `template_code` 自动生成
      - Required: `template_name`, `category`
      - Optional: `template_description`, `dictionaries`
    
    - **List**: GET /api/data-template/
      - 支持分页: ?page=1&page_size=10
    
    - **Retrieve**: GET /api/data-template/{template_code}/
      - 返回模板详情，包括关联的词条列表
    
    - **Update**: PUT /api/data-template/{template_code}/
      - 可更新：template_name, template_description, category, dictionaries
    
    - **Delete**: DELETE /api/data-template/{template_code}/
    """
    queryset = DataTemplate.objects.all().order_by('template_code')
    serializer_class = DataTemplateSerializer
    lookup_field = 'template_code'
    pagination_class = StandardPagination

class ArchiveViewSet(CustomModelViewSet):
    """
    API endpoint for 专病档案管理.

    - **Create**: POST /api/archive/
      - `archive_code` 自动生成
      - Required: `archive_name`, `archive_description`

      请求示例:
      ```json
      {
          "archive_name": "string",
          "archive_description": "string"
      }
      ```

      实际示例:
      ```json
      {
          "archive_name": "肾移植档案",
          "archive_description": "收集肾移植患者的术前术后检查数据"
      }
      ```

      响应示例:
      ```json
      {
          "code": 200,
          "msg": "创建成功",
          "data": {
              "archive_code": "A000001",
              "archive_name": "肾移植档案",
              "archive_description": "收集肾移植患者的术前术后检查数据",
              "created_at": "2025-05-27T10:00:00"
          }
      }
      ```
    
    - **List**: GET /api/archive/
      - 支持分页: ?page=1&page_size=10
      - 返回档案基本信息和包含的病例数

      响应示例:
      ```json
      {
          "code": 200,
          "msg": "查询成功",
          "data": {
              "list": [
                  {
                      "archive_code": "A000001",
                      "archive_name": "肾移植档案",
                      "archive_description": "收集肾移植患者的术前术后检查数据",
                      "case_count": 10,
                      "created_at": "2025-05-27T10:00:00"
                  }
              ],
              "total": 1,
              "page": 1,
              "page_size": 10
          }
      }
      ```
    
    - **Retrieve**: GET /api/archive/{archive_code}/
      - 返回档案详细信息

      响应示例:
      ```json
      {
          "code": 200,
          "msg": "查询成功",
          "data": {
              "archive_code": "A000001",
              "archive_name": "肾移植档案",
              "archive_description": "收集肾移植患者的术前术后检查数据",
              "created_at": "2025-05-27T10:00:00",
              "cases": [
                  {
                      "case_code": "C000001",
                      "name": "张三",
                      "gender": "男",
                      "age": 45
                  }
              ]
          }
      }
      ```
    
    - **Update**: PUT /api/archive/{archive_code}/
      - 可更新：archive_name, archive_description

      请求示例:
      ```json
      {
          "archive_name": "肾移植随访档案",
          "archive_description": "收集肾移植患者的术前术后以及随访检查数据"
      }
      ```

      响应示例:
      ```json
      {
          "code": 200,
          "msg": "更新成功",
          "data": {
              "archive_code": "A000001",
              "archive_name": "肾移植随访档案",
              "archive_description": "收集肾移植患者的术前术后以及随访检查数据",
              "created_at": "2025-05-27T10:00:00"
          }
      }
      ```
    
    - **Delete**: DELETE /api/archive/{archive_code}/

      响应示例:
      ```json
      {
          "code": 200,
          "msg": "删除成功",
          "data": null
      }
      ```

    ## 错误响应示例
    ```json
    {
        "code": 400,
        "msg": "请求参数错误",
        "data": {
            "archive_name": ["该字段是必填项。"],
            "archive_description": ["该字段是必填项。"]
        }
    }
    """
    queryset = Archive.objects.all().order_by('archive_code')
    serializer_class = ArchiveSerializer
    lookup_field = 'archive_code'
    pagination_class = StandardPagination

    def get_serializer_class(self):
        """根据不同的操作使用不同的序列化器"""
        if self.action == 'list':
            return ArchiveListSerializer
        elif self.action == 'retrieve':
            return ArchiveDetailSerializer
        return ArchiveSerializer

class CaseViewSet(CustomModelViewSet):
    """
    API endpoint for 病例管理.

    - **Create**: POST /api/case/
      - `case_code` 自动生成
      - Required: `identity`, `name`, `gender`, `birth_date`
      - Optional: `opd_id`, `inhospital_id`, `phone_number`, `home_address`, `blood_type`, 
                 `main_diagnosis`, `has_transplant_surgery`, `is_in_transplant_queue`, `archives`
    
    - **List**: GET /api/case/
      - 支持分页: ?page=1&page_size=10
      - 支持模糊搜索: ?search=xxx（可模糊搜索档案编号、身份证号、门诊号、住院号、姓名）
    
    - **Retrieve**: GET /api/case/{case_code}/
      - 返回病例详细信息，包括关联的档案
    
    - **Update**: PUT /api/case/{case_code}/
      - 可更新除case_code外的所有字段
    
    - **Delete**: DELETE /api/case/{case_code}/
      - 删除病例及其相关数据
      - 如果删除的病例是该患者的最后一个病例，则同时删除患者信息
    
    - **Identity Cases**: GET /api/case/identity/{identity_id}/
      - 获取指定身份证号的所有病例
    """
    queryset = Case.objects.all().order_by('case_code')
    serializer_class = CaseSerializer
    lookup_field = 'case_code'
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return CaseListSerializer
        elif self.action == 'retrieve':
            return CaseDetailSerializer
        return CaseSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            # 支持搜索档案编号、身份证号、门诊号、住院号、姓名
            return queryset.filter(
                Q(archives__archive_code__icontains=search) |
                Q(identity__identity_id__icontains=search) |
                Q(opd_id__icontains=search) |
                Q(inhospital_id__icontains=search) |
                Q(name__icontains=search)
            ).distinct()
        return queryset

    @swagger_auto_schema(
        operation_description="删除病例。如果删除的病例是该患者的最后一个病例，则同时删除患者信息。",
        responses={
            200: openapi.Response(
                description="成功删除病例",
                examples={
                    "application/json": {
                        "code": 200,
                        "msg": "删除成功",
                        "data": {
                            "deleted_case_code": "C000031",
                            "deleted_patient": True,
                            "patient_identity_id": "XXXXXXXXXXXXXX"
                        }
                    }
                }
            ),
            404: '病例不存在',
            500: '删除失败'
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除病例，如果删除的病例是该患者的最后一个病例，则同时删除患者信息
        """
        try:
            instance = self.get_object()
            
            # 获取患者信息
            patient = instance.identity
            patient_identity_id = patient.identity_id
            
            # 删除病例（这会级联删除相关的DataTable、ArchiveCase、Images等）
            self.perform_destroy(instance)
            
            # 删除病例后，重新检查该患者是否还有其他病例
            remaining_cases = Case.objects.filter(identity=patient)
            
            # 如果删除后该患者没有其他病例了，则删除患者信息
            if not remaining_cases.exists():
                patient.delete()
                return APIResponse(
                    response_code=ResponseCode.SUCCESS,
                    data={
                        "deleted_case_code": instance.case_code,
                        "deleted_patient": True,
                        "patient_identity_id": patient_identity_id,
                        "message": f"已删除病例 {instance.case_code} 和患者 {patient_identity_id}（该患者的最后一个病例）"
                    }
                )
            else:
                return APIResponse(
                    response_code=ResponseCode.SUCCESS,
                    data={
                        "deleted_case_code": instance.case_code,
                        "deleted_patient": False,
                        "patient_identity_id": patient_identity_id,
                        "remaining_cases_count": remaining_cases.count(),
                        "message": f"已删除病例 {instance.case_code}，患者 {patient_identity_id} 还有其他 {remaining_cases.count()} 个病例"
                    }
                )
                
        except Exception as e:
            return APIResponse(response_code=ResponseCode.INTERNAL_ERROR, data=str(e))

    @action(detail=False, url_path='identity/(?P<identity_id>[^/.]+)')
    def identity_cases(self, request, identity_id=None):
        """获取指定身份证号的所有病例"""
        cases = Case.objects.filter(identity__identity_id=identity_id)
        page = self.paginate_queryset(cases)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(cases, many=True)
        return Response(serializer.data)

class IdentityViewSet(mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.ListModelMixin,
                     GenericViewSet):
    """
    API endpoint for 患者管理.

    只支持患者信息的查询和更新，不支持创建和删除。
    患者信息会在创建病例时自动创建或更新。

    - **List**: GET /api/patient/
      - 支持分页和模糊搜索：?search=xxx（可模糊搜索身份证号、姓名）
    
    - **Retrieve**: GET /api/patient/{identity_id}/
      - 返回患者详情及其所有病例
    
    - **Update**: PUT /api/patient/{identity_id}/
      - 可更新患者的基本信息
    """
    queryset = Identity.objects.all()
    serializer_class = IdentitySerializer
    lookup_field = 'identity_id'
    pagination_class = StandardPagination

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'search', openapi.IN_QUERY, description="模糊搜索身份证号或姓名", type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'page_size', openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_INTEGER
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PatientDetailSerializer
        return IdentitySerializer

    @action(detail=True, url_path='case-data')
    def case_data(self, request, identity_id=None):
        """获取患者所有病例的数据"""
        identity = self.get_object()
        cases = Case.objects.filter(identity=identity)
        
        # 获取case_ids
        case_ids = list(cases.values_list('id', flat=True))
        
        # 查询所有相关数据
        data_tables = DataTable.objects.filter(
            case_id__in=case_ids
        ).select_related(
            'case',
            'data_template',
            'data_template__category',
            'dictionary'
        ).order_by('case_id', 'check_time')

        # 序列化数据
        serializer = DataTableDetailSerializer(data_tables, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            return queryset.filter(
                Q(identity_id__icontains=search) |
                Q(name__icontains=search)
            )
        return queryset

class DataTableViewSet(CustomModelViewSet):
    """
    数据管理接口，支持单条和批量录入临床数据。

    ## 主要功能
    1. 数据录入 - 支持两种模式：单条录入和批量录入
    2. 数据查询 - 支持分页和按病例编号过滤
    3. 数据详情查看

    ## 接口说明

    ### 1. 单条数据录入
    POST /api/data/
    
    请求参数说明：
    - case_code: 病例编号
    - template_code: 模板编号
    - word_code: 词条编号
    - check_time: 检查时间，格式：YYYY-MM-DD HH:MM:SS
    - value: 数据值

    请求示例：
    ```json
    {
        "case_code": "C000001",
        "template_code": "T000001",
        "word_code": "A000001",
        "check_time": "2025-05-25 14:30:00",
        "value": "检查值"
    }
    ```

    响应示例：
    ```json
    {
        "code": 200,
        "msg": "操作成功",
        "data": {
            "id": 123,
            "case_code": "C000001",
            "template_category": "分类1",
            "template_name": "测试",
            "word_name": "string",
            "value": "检查值",
            "check_time": "2025-05-25 14:30:00"
        }
    }
    ```

    ### 2. 批量数据录入
    POST /api/data/
    
    请求参数说明：
    - case_code: 病例编号
    - template_code: 模板编号
    - data_list: 数据列表，每项包含：
        - word_code: 词条编号
        - check_time: 检查时间，格式：YYYY-MM-DD HH:MM:SS
        - value: 数据值

    请求示例：
    ```json
    {
        "case_code": "C000001",
        "template_code": "T000001",
        "data_list": [
            {
                "word_code": "A000001",
                "check_time": "2025-05-25 14:30:00",
                "value": "值1"
            },
            {
                "word_code": "A000002",
                "check_time": "2025-05-25 15:30:00",
                "value": "值2"
            }
        ]
    }
    ```

    响应示例：
    ```json
    {
        "code": 200,
        "msg": "操作成功",
        "data": {
            "message": "成功创建 2 条数据记录",
            "data": [
                {
                    "id": 123,
                    "case_code": "C000001",
                    "template_category": "分类1",
                    "template_name": "测试",
                    "word_name": "string",
                    "value": "值1",
                    "check_time": "2025-05-25 14:30:00"
                },
                {
                    "id": 124,
                    "case_code": "C000001",
                    "template_category": "分类1",
                    "template_name": "测试",
                    "word_name": "string",
                    "value": "值2",
                    "check_time": "2025-05-25 15:30:00"
                }
            ]
        }
    }
    ```
    """
    queryset = DataTable.objects.all()
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == 'create':
            # 根据请求数据结构判断使用哪个序列化器
            if self.request.data.get('data_list'):
                return DataTableBulkCreateSerializer
            return DataTableSerializer
        return DataTableDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        case_code = self.request.query_params.get('case_code', None)
        if case_code:
            queryset = queryset.filter(case__case_code=case_code)
        return queryset.select_related('case', 'data_template', 'dictionary')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # 如果是批量创建，直接返回序列化器的表示
        if isinstance(instance, list):
            return Response({
                'code': 200,
                'msg': '操作成功',
                'data': serializer.data
            })
        
        # 如果是单条创建，使用DataTableDetailSerializer序列化返回
        detail_serializer = DataTableDetailSerializer(instance)
        return Response({
            'code': 200,
            'msg': '操作成功',
            'data': detail_serializer.data
        })

class DataTemplateCategoryViewSet(CustomModelViewSet):
    """
    API endpoint for 数据模板分类管理.

    - **Create**: POST /api/template-category/
      - Required: `name`
      - Optional: none
    
    - **List**: GET /api/template-category/
      - 支持分页: ?page=1&page_size=10
    
    - **Retrieve**: GET /api/template-category/{id}/
      - 返回模板分类详情
    
    - **Update**: PUT /api/template-category/{id}/
      - 可更新：name
    
    - **Delete**: DELETE /api/template-category/{id}/
    """
    queryset = DataTemplateCategory.objects.all().order_by('id')
    serializer_class = DataTemplateCategorySerializer
    pagination_class = StandardPagination


@action(detail=False, methods=['get'])
def download_template(self, request):
    """
    下载词条导入模板
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="dictionary_import_template.csv"'

    template_path = 'resources/dictionary_import_template.csv'
    with open(template_path, 'r', encoding='utf-8-sig') as file:
        response.write(file.read())

    return response

@action(detail=False, methods=['post'])
def bulk_import(self, request):
    """
    批量导入词条
    """
    serializer = DictionaryBulkImportSerializer(data=request.data)
    if serializer.is_valid():
        result = serializer.save()
        return Response({
            'code': 200,
            'msg': f"成功导入{result['success_count']}条词条，失败{result['error_count']}条",
            'data': result
        })
    return Response({
        'code': 400,
        'msg': "导入失败",
        'data': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

class PatientMergedCaseListView(APIView):
    """
    获取患者列表（每个患者只展示一行，字段为所有病例中最新非空值，仅支持分页，不支持搜索）
    支持通过档案编号筛选
    """
    pagination_class = StandardPagination

    class PatientMergedCaseListPaginationSerializer(serializers.Serializer):
        page = serializers.IntegerField(default=1, help_text="页码")
        page_size = serializers.IntegerField(default=10, help_text="每页数量")
        archive_code = serializers.CharField(required=False, help_text="档案编号，用于筛选")

    @swagger_auto_schema(
        operation_description="获取患者列表，每个患者只展示一行，字段为所有病例中最新非空值。支持分页和档案编号筛选。",
        manual_parameters=[
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="页码",
                type=openapi.TYPE_INTEGER,
                default=1
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="每页数量",
                type=openapi.TYPE_INTEGER,
                default=10
            ),
            openapi.Parameter(
                'archive_code',
                openapi.IN_QUERY,
                description="档案编号，用于筛选特定档案下的患者",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description="模糊搜索患者姓名或身份证号",
                type=openapi.TYPE_STRING,
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description="成功返回患者列表数据",
                examples={
                    "application/json": {
                        "code": 200,
                        "msg": "操作成功",
                        "data": {
                            "list": [
                                {
                                    "identity_id": "XXXXXXXXXXXXXX",
                                    "name": "王XXX",
                                    "gender": 0,
                                    "birth_date": "1972-01-01",
                                    "age": 52,
                                    "case_id": 1,
                                    "case_code": "XA568942",
                                    "phone_number": "18956142356",
                                    "home_address": "福建省厦门市XXXXXXXXXXXXX",
                                    "blood_type": "O型",
                                    "has_transplant_surgery": "是(2024-XX-XX)",
                                    "is_in_transplant_queue": "否"
                                }
                            ],
                            "total": 1,
                            "page": 1,
                            "page_size": 10
                        }
                    }
                }
            ),
            404: openapi.Response(
                description="档案不存在",
                examples={
                    "application/json": {
                        "code": 404,
                        "msg": "未找到档案编号为 A000001 的档案",
                        "data": None
                    }
                }
            )
        }
    )
    def get(self, request):
        # 获取查询参数
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        archive_code = request.query_params.get('archive_code')
        search = request.query_params.get('search')

        # 构建基础查询
        queryset = Identity.objects.all()

        # 如果提供了档案编号，进行筛选
        if archive_code:
            try:
                archive = Archive.objects.get(archive_code=archive_code)
                # 获取该档案下的所有病例的身份证号
                identity_ids = Case.objects.filter(
                    archives=archive
                ).values_list('identity_id', flat=True).distinct()
                queryset = queryset.filter(identity_id__in=identity_ids)
            except Archive.DoesNotExist:
                return Response({
                    'code': 404,
                    'msg': f'未找到档案编号为 {archive_code} 的档案',
                    'data': None
                })

        # 如果提供了search参数，进行姓名或身份证号模糊查询
        if search:
            queryset = queryset.filter(
                Q(identity_id__icontains=search) | Q(name__icontains=search)
            )

        # 获取所有符合条件的患者
        patients = []
        for identity in queryset:
            # 获取该患者的所有病例
            cases = Case.objects.filter(identity=identity)
            
            # 如果提供了档案编号，只获取该档案下的病例
            if archive_code:
                cases = cases.filter(archives__archive_code=archive_code)

            if not cases.exists():
                continue

            # 获取最新病例
            latest_case = cases.order_by('-id').first()

            # 构建患者数据
            patient_data = {
                'identity_id': identity.identity_id,
                'name': identity.name,
                'gender': identity.gender,
                'birth_date': identity.birth_date,
                'age': (date.today().year - identity.birth_date.year) - 
                      ((date.today().month, date.today().day) < 
                       (identity.birth_date.month, identity.birth_date.day)),
                'case_id': latest_case.id,
                'case_code': latest_case.case_code,
                'phone_number': latest_case.phone_number,
                'home_address': latest_case.home_address,
                'blood_type': latest_case.blood_type,
                'has_transplant_surgery': latest_case.has_transplant_surgery,
                'is_in_transplant_queue': latest_case.is_in_transplant_queue
            }
            patients.append(patient_data)

        # 分页处理
        total = len(patients)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_patients = patients[start:end]

        return Response({
            'code': 200,
            'msg': '操作成功',
            'data': {
                'list': paginated_patients,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        })

class CaseTemplateSummaryView(APIView):
    """
    接收一个或多个case_code，返回这些病例的所有数据模板下的数据，
    包含模板分类、模板名称、模板编号、检查时间。
    
    注意：同一模板下不同的检查时间会分别返回，每个（模板，检查时间）组合为一条数据。
    检查时间精确到时分秒（YYYY-MM-DD HH:MM:SS）。
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="传入一个或多个病例编号（case_code），返回这些病例的所有数据模板下的数据，包含模板分类、模板名称、模板编号、检查时间。\n\n注意：同一模板下不同的检查时间会分别返回，每个（模板，检查时间）组合为一条数据。\n\n检查时间精确到时分秒（YYYY-MM-DD HH:MM:SS）。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['case_codes'],
            properties={
                'case_codes': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description='病例编号列表，如[\"XA568942\", \"XA584523\"]'
                )
            },
            example={
                'case_codes': ['C000001', 'C000002']
            }
        ),
        responses={
            200: openapi.Response(
                description="成功返回模板分组数据",
                examples={
                    "application/json": {
                        "code": 200,
                        "msg": "操作成功",
                        "data": [
                            {
                                "template_category": "临床检验",
                                "templates": [
                                    {
                                        "template_name": "血常规",
                                        "template_code": "T000001",
                                        "check_time": "2024-06-01 12:21:00"
                                    },
                                    {
                                        "template_name": "血常规",
                                        "template_code": "T000001",
                                        "check_time": "2024-06-02 09:30:00"
                                    },
                                    {
                                        "template_name": "凝血四项",
                                        "template_code": "T000002",
                                        "check_time": "2024-06-01 08:00:00"
                                    }
                                ]
                            },
                            {
                                "template_category": "辅助检查",
                                "templates": [
                                    {
                                        "template_name": "胸部CT",
                                        "template_code": "T000003",
                                        "check_time": "2024-06-03 15:00:00"
                                    }
                                ]
                            }
                        ]
                    }
                }
            ),
            400: '参数错误',
            404: '未找到相关病例'
        }
    )
    def post(self, request):
        case_codes = request.data.get('case_codes', [])
        if not case_codes or not isinstance(case_codes, list):
            return Response({
                'code': 400,
                'msg': '请提供case_codes列表',
                'data': None
            }, status=400)

        # 查询所有相关病例id
        from .models import Case, DataTable
        case_id_map = {c.case_code: c.id for c in Case.objects.filter(case_code__in=case_codes)}
        if not case_id_map:
            return Response({
                'code': 404,
                'msg': '未找到相关病例',
                'data': None
            }, status=404)
        case_ids = list(case_id_map.values())

        # 查询所有相关数据表数据
        data_tables = DataTable.objects.filter(case_id__in=case_ids).select_related(
            'data_template', 'data_template__category'
        )

        # 组装分组结构: 分类->模板+检查时间
        result = {}
        for dt in data_tables:
            category = dt.data_template.category.name if dt.data_template and dt.data_template.category else None
            template_name = dt.data_template.template_name if dt.data_template else None
            template_code = dt.data_template.template_code if dt.data_template else None
            check_time = dt.check_time.strftime('%Y-%m-%d %H:%M:%S') if dt.check_time else None
            if not (category and template_name and template_code and check_time):
                continue
            if category not in result:
                result[category] = []
            # 判断同一模板同一检查时间是否已存在
            exists = any(
                t['template_code'] == template_code and t['check_time'] == check_time
                for t in result[category]
            )
            if not exists:
                result[category].append({
                    'template_name': template_name,
                    'template_code': template_code,
                    'check_time': check_time
                })

        # 转换为前端需要的结构
        data = []
        for category, templates in result.items():
            data.append({
                'template_category': category,
                'templates': templates
            })

        return Response({
            'code': 200,
            'msg': '操作成功',
            'data': data
        })

class CaseTemplateDetailView(APIView):
    """
    查询某病例下某模板某次检查的所有词条及其值（详情）。
    
    现在需要传入case_code、template_code和check_time三者，唯一确定一次检查。
    检查时间精确到时分秒（YYYY-MM-DD HH:MM:SS）。
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="传入病例编号、模板编号和检查时间，返回该病例下该模板该次检查的所有词条及其值、检查时间、模板名称。\n\n注意：check_time为必填，精确到时分秒。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['case_code', 'template_code', 'check_time'],
            properties={
                'case_code': openapi.Schema(type=openapi.TYPE_STRING, description='病例编号'),
                'template_code': openapi.Schema(type=openapi.TYPE_STRING, description='模板编号'),
                'check_time': openapi.Schema(type=openapi.TYPE_STRING, description='检查时间，格式YYYY-MM-DD HH:MM:SS')
            },
            example={
                'case_code': 'C000001',
                'template_code': 'T000001',
                'check_time': '2024-06-01 12:21:00'
            }
        ),
        responses={
            200: openapi.Response(
                description="成功返回模板详情",
                examples={
                    "application/json": {
                        "code": 200,
                        "msg": "操作成功",
                        "data": {
                            "template_name": "血常规",
                            "check_time": "2024-06-01 12:21:00",
                            "items": [
                                {"word_code": "A000001", "word_name": "白细胞", "value": "5.6"},
                                {"word_code": "A000002", "word_name": "红细胞", "value": "4.2"}
                            ]
                        }
                    }
                }
            ),
            400: '参数错误',
            404: '未找到相关数据'
        }
    )
    def post(self, request):
        case_code = request.data.get('case_code')
        template_code = request.data.get('template_code')
        check_time = request.data.get('check_time')
        if not case_code or not template_code or not check_time:
            return Response({
                'code': 400,
                'msg': '请提供case_code、template_code和check_time',
                'data': None
            }, status=400)
        from .models import Case, DataTemplate, DataTable, Dictionary
        from django.utils.dateparse import parse_datetime
        try:
            case = Case.objects.get(case_code=case_code)
            template = DataTemplate.objects.get(template_code=template_code)
        except (Case.DoesNotExist, DataTemplate.DoesNotExist):
            return Response({
                'code': 404,
                'msg': '未找到相关病例或模板',
                'data': None
            }, status=404)
        # 检查时间精确过滤
        try:
            dt_check_time = parse_datetime(check_time)
        except Exception:
            dt_check_time = None
        if not dt_check_time:
            return Response({
                'code': 400,
                'msg': 'check_time格式错误，需为YYYY-MM-DD HH:MM:SS',
                'data': None
            }, status=400)
        # 查找所有该病例下该模板该检查时间的数据
        data_tables = DataTable.objects.filter(case=case, data_template=template, check_time=dt_check_time).select_related('dictionary')
        if not data_tables.exists():
            return Response({
                'code': 404,
                'msg': '未找到相关数据',
                'data': None
            }, status=404)
        items = []
        from .serializers import DictionarySerializer
        for dt in data_tables:
            dict_data = DictionarySerializer(dt.dictionary).data
            dict_data['value'] = dt.value
            items.append(dict_data)
        return Response({
            'code': 200,
            'msg': '操作成功',
            'data': {
                'template_name': template.template_name,
                'check_time': check_time,
                'items': items
            }
        })

class CaseVisualizationDataView(APIView):
    """
    根据选择的X轴（时间）和Y轴（词条编号），返回对应的数据值。
    X轴数据来源：从data表获取所有数据，取出这些数据的检查时间。
    Y轴数据来源：从data表获取所有数据，根据dictionary_id找出这些词条名称，过滤条件是该词条的data_type为数值类型。
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="根据选择的X轴（时间）和Y轴（词条编号），返回对应的数据值。",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['case_code', 'x_axis_times', 'y_axis_word_codes'],
            properties={
                'case_code': openapi.Schema(type=openapi.TYPE_STRING, description='病例编号'),
                'x_axis_times': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description='X轴时间数组，例如["2025-06-18 04:36:00", "2025-06-19 04:41:00"]'
                ),
                'y_axis_word_codes': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description='Y轴词条编号数组，例如["TES000018", "TES000019"]'
                )
            },
            example={
                'case_code': 'C000001',
                'x_axis_times': [
                    '2025-06-18 04:36:00',
                    '2025-06-19 04:41:00',
                    '2025-06-20 04:17:00',
                    '2025-06-22 04:25:00'
                ],
                'y_axis_word_codes': ['TES000018']
            }
        ),
        responses={
            200: openapi.Response(
                description="成功返回可视化数据",
                examples={
                    "application/json": {
                        "code": 200,
                        "msg": "操作成功",
                        "data": [
                            {
                                "word_code": "TES000018",
                                "word_name": "白细胞",
                                "data_points": [
                                    {"check_time": "2025-06-18 04:36:00", "value": "5.6"},
                                    {"check_time": "2025-06-19 04:41:00", "value": "6.1"}
                                ]
                            }
                        ]
                    }
                }
            ),
            400: '参数错误',
            404: '未找到相关数据'
        }
    )
    def post(self, request):
        case_code = request.data.get('case_code')
        x_axis_times = request.data.get('x_axis_times', [])
        y_axis_word_codes = request.data.get('y_axis_word_codes', [])

        if not case_code or not x_axis_times or not y_axis_word_codes:
            return Response({
                'code': 400,
                'msg': '请提供case_code, x_axis_times和y_axis_word_codes',
                'data': None
            }, status=400)

        from .models import Case, DataTable, Dictionary
        from .serializers import CaseVisualizationDataSerializer
        from django.utils.dateparse import parse_datetime

        try:
            case = Case.objects.get(case_code=case_code)
        except Case.DoesNotExist:
            return Response({
                'code': 404,
                'msg': '未找到相关病例',
                'data': None
            }, status=404)

        # 将x_axis_times字符串转为datetime
        x_axis_datetimes = [parse_datetime(t) for t in x_axis_times if parse_datetime(t)]

        result_data = []
        for y_word_code in y_axis_word_codes:
            try:
                dictionary = Dictionary.objects.get(word_code=y_word_code, data_type='数值类型')
            except Dictionary.DoesNotExist:
                continue
            # 获取该病例、该词条在这些时间点的数据
            data_points_queryset = DataTable.objects.filter(
                case=case,
                dictionary=dictionary,
                check_time__in=x_axis_datetimes
            ).order_by('check_time')

            data_points = []
            for dp in data_points_queryset:
                data_points.append({
                    'check_time': dp.check_time.strftime('%Y-%m-%d %H:%M:%S') if dp.check_time else None,
                    'value': dp.value
                })

            result_data.append({
                'word_code': dictionary.word_code,
                'word_name': dictionary.word_name,
                'data_points': data_points
            })

        if not result_data:
            return Response({
                'code': 404,
                'msg': '未找到符合条件的图表数据',
                'data': None
            }, status=404)

        return Response({
            'code': 200,
            'msg': '操作成功',
            'data': CaseVisualizationDataSerializer(result_data, many=True).data
        })

class CaseVisualizationYAxisTimesView(APIView):
    """
    根据病例编号查询Y轴选项（所有数值型词条），按模板分组返回
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="根据病例编号查询Y轴选项（所有数值型词条），按模板分组返回",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['case_code'],
            properties={
                'case_code': openapi.Schema(type=openapi.TYPE_STRING, description='病例编号'),
            },
            example={
                'case_code': 'C000001'
            }
        ),
        responses={
            200: openapi.Response(
                description="成功返回Y轴选项（按模板分组的数值型词条）",
                examples={
                    "application/json": {
                        "code": 200,
                        "msg": "操作成功",
                        "data": [
                            {
                                "template_name": "血常规",
                                "template_code": "T000001",
                                "dictionaries": [
                                    {"word_code": "A000001", "word_name": "白细胞"},
                                    {"word_code": "A000002", "word_name": "红细胞"}
                                ]
                            },
                            {
                                "template_name": "凝血四项",
                                "template_code": "T000002",
                                "dictionaries": [
                                    {"word_code": "B000001", "word_name": "血压"},
                                    {"word_code": "B000002", "word_name": "心率"}
                                ]
                            }
                        ]
                    }
                }
            ),
            400: '参数错误',
            404: '未找到相关数据'
        }
    )
    def post(self, request):
        case_code = request.data.get('case_code')
        if not case_code:
            return Response({
                'code': 400,
                'msg': '请提供case_code',
                'data': None
            }, status=400)

        from .models import Case, Dictionary, DataTable
        from .serializers import CaseVisualizationOptionSerializer
        try:
            case = Case.objects.get(case_code=case_code)
        except Case.DoesNotExist:
            return Response({
                'code': 404,
                'msg': '未找到相关病例',
                'data': None
            }, status=404)

        # 查询该病例下所有数值型词条，按模板分组
        data_tables = DataTable.objects.filter(
            case=case,
            dictionary__data_type='数值类型'
        ).select_related(
            'data_template',
            'dictionary'
        ).distinct()

        # 按模板分组
        template_groups = {}
        seen_dictionaries = set()  # 用于去重
        for dt in data_tables:
            if dt.data_template:
                template_key = f"{dt.data_template.template_code}_{dt.data_template.template_name}"
                if template_key not in template_groups:
                    template_groups[template_key] = {
                        'template_name': dt.data_template.template_name,
                        'template_code': dt.data_template.template_code,
                        'dictionaries': []
                    }
                
                # 检查是否已添加该词条（去重）
                if dt.dictionary.word_code not in seen_dictionaries:
                    seen_dictionaries.add(dt.dictionary.word_code)
                    template_groups[template_key]['dictionaries'].append({
                        'word_code': dt.dictionary.word_code,
                        'word_name': dt.dictionary.word_name
                    })

        # 转换为前端需要的格式
        result_data = list(template_groups.values())

        return Response({
            'code': 200,
            'msg': '操作成功',
            'data': result_data
        })

class CaseVisualizationXAxisOptionsView(APIView):
    """
    根据病例编号查询X轴选项（所有有数据的时间点，精确到秒）。
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="根据病例编号查询X轴选项（所有有数据的时间点，精确到秒）",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['case_code', 'y_axis_word_code'],
            properties={
                'case_code': openapi.Schema(type=openapi.TYPE_STRING, description='病例编号'),
                'y_axis_word_code': openapi.Schema(type=openapi.TYPE_STRING, description='Y轴选中的词条编号'),
            },
            example={
                'case_code': 'C000001',
                'y_axis_word_code': 'TES000018'
            }
        ),
        responses={
            200: openapi.Response(
                description="成功返回X轴选项（所有有数据的时间点）",
                examples={
                    "application/json": {
                        "code": 200,
                        "msg": "操作成功",
                        "data": {
                            "x_axis_options": [
                                "2025-06-18 04:36:00",
                                "2025-06-19 04:41:00"
                            ]
                        }
                    }
                }
            ),
            400: '参数错误',
            404: '未找到相关数据'
        }
    )
    def post(self, request):
        case_code = request.data.get('case_code')
        y_axis_word_code = request.data.get('y_axis_word_code')
        if not case_code or not y_axis_word_code:
            return Response({
                'code': 400,
                'msg': '请提供case_code和y_axis_word_code',
                'data': None
            }, status=400)

        from .models import Case, DataTable, Dictionary
        try:
            case = Case.objects.get(case_code=case_code)
            dictionary = Dictionary.objects.get(word_code=y_axis_word_code, data_type='数值类型')
        except (Case.DoesNotExist, Dictionary.DoesNotExist):
            return Response({
                'code': 404,
                'msg': '未找到相关病例或词条',
                'data': None
            }, status=404)

        # 查询该病例该词条下所有有数据的check_time
        check_times = DataTable.objects.filter(case=case, dictionary=dictionary).values_list('check_time', flat=True).distinct().order_by('check_time')
        x_axis_options = [ct.strftime('%Y-%m-%d %H:%M:%S') for ct in check_times if ct]

        return Response({
            'code': 200,
            'msg': '操作成功',
            'data': {
                'x_axis_options': x_axis_options
            }
        })

class DataTableCRUDView(APIView):
    """
    数据表的增删改查接口，根据病例编号、模板编号、词条编号、检查时间共同确定一条数据。
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="根据病例编号、词条编号、检查时间查询数据。\n\n如果不传template_code，则返回所有相关数据（即所有匹配病例编号、词条编号的数据，check_time不是必填项），返回格式为 {\"list\": [...]}。\n\n- case_code: 必填，病例编号\n- word_code: 必填，词条编号\n- template_code: 可选，模板编号。如果不传，则不作为过滤条件。\n- check_time: 可选，检查时间。\n\n返回格式为 {list: [...]}。\n\n【注意】template_code 现在是可选参数，不传时会返回所有匹配病例编号和词条编号的数据。",
        manual_parameters=[
            openapi.Parameter('case_code', openapi.IN_QUERY, description="病例编号", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('template_code', openapi.IN_QUERY, description="模板编号（可选）", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('word_code', openapi.IN_QUERY, description="词条编号", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('check_time', openapi.IN_QUERY, description="检查时间，格式YYYY-MM-DD HH:MM:SS（可选，不传则返回所有相关数据，返回格式为 {list: [...]})", type=openapi.TYPE_STRING, required=False),
        ],
        responses={
            200: openapi.Response(
                description="成功返回数据",
                examples={
                    "application/json": {
                        "code": 200,
                        "msg": "查询成功",
                        "data": {
                            "list": [
                                {
                                    "id": 3000,
                                    "case_code": "C000039",
                                    "template_code": "T000001",
                                    "word_code": "TES000022",
                                    "word_name": "总胆红素",
                                    "value": "178",
                                    "check_time": "2025-05-25 15:30:00"
                                }
                            ]
                        }
                    }
                }
            ),
            400: '参数错误',
            404: '未找到相关数据'
        }
    )
    def get(self, request):
        """查询数据（template_code 现在是可选参数，不传时不作为过滤条件）"""
        case_code = request.query_params.get('case_code')
        template_code = request.query_params.get('template_code')  # 可选
        word_code = request.query_params.get('word_code')
        check_time = request.query_params.get('check_time')
        
        if not all([case_code, word_code]):
            return Response({
                'code': 400,
                'msg': '请提供case_code和word_code',
                'data': None
            }, status=400)

        from .models import Case, DataTemplate, Dictionary, DataTable
        from django.utils.dateparse import parse_datetime
        try:
            case = Case.objects.get(case_code=case_code)
            dictionary = Dictionary.objects.get(word_code=word_code)
        except (Case.DoesNotExist, Dictionary.DoesNotExist) as e:
            return Response({
                'code': 404,
                'msg': f'未找到相关数据: {str(e)}',
                'data': None
            }, status=404)

        queryset = DataTable.objects.filter(
            case=case,
            dictionary=dictionary
        )
        # 只有当 template_code 提供时才作为过滤条件
        if template_code:
            try:
                template = DataTemplate.objects.get(template_code=template_code)
                queryset = queryset.filter(data_template=template)
            except DataTemplate.DoesNotExist as e:
                return Response({
                    'code': 404,
                    'msg': f'未找到相关模板: {str(e)}',
                    'data': None
                }, status=404)
        if check_time:
            dt_check_time = parse_datetime(check_time)
            if not dt_check_time:
                return Response({
                    'code': 400,
                    'msg': 'check_time格式错误，需为YYYY-MM-DD HH:MM:SS',
                    'data': None
                }, status=400)
            queryset = queryset.filter(check_time=dt_check_time)

        if not queryset.exists():
            return Response({
                'code': 404,
                'msg': '未找到相关数据',
                'data': None
            }, status=404)

        data = [
            {
                'id': dt.id,
                'case_code': case_code,
                'template_code': dt.data_template.template_code if dt.data_template else None,
                'word_code': word_code,
                'word_name': dictionary.word_name,
                'value': dt.value,
                'check_time': dt.check_time.strftime('%Y-%m-%d %H:%M:%S') if dt.check_time else None
            }
            for dt in queryset
        ]
        return Response({
            'code': 200,
            'msg': '查询成功',
            'data': {'list': data}
        })

    @swagger_auto_schema(
        operation_description="""
        创建新数据，支持单条和批量导入。
        
        - 单条数据格式：
        {
            "case_code": "C000001",
            "template_code": "T000001",
            "word_code": "A000001",
            "check_time": "2025-06-18 04:36:00",
            "value": "5.6"
        }
        
        - 批量数据格式：
        {
            "case_code": "C000001",
            "template_code": "T000001",
            "data_list": [
                {
                    "word_code": "A000001",
                    "check_time": "2025-05-25 14:30:00",
                    "value": "值1"
                },
                {
                    "word_code": "A000002",
                    "check_time": "2025-05-25 15:30:00",
                    "value": "值2"
                }
            ]
        }
        
        - 返回：
          - 单条：{"code":200, "msg":"创建成功", "data":{...}}
          - 批量：{"code":200, "msg":"创建成功", "data":{...}}
        """,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'case_code': openapi.Schema(type=openapi.TYPE_STRING, description='病例编号'),
                'template_code': openapi.Schema(type=openapi.TYPE_STRING, description='模板编号'),
                'word_code': openapi.Schema(type=openapi.TYPE_STRING, description='词条编号（单条时必填）'),
                'check_time': openapi.Schema(type=openapi.TYPE_STRING, description='检查时间（单条时必填）'),
                'value': openapi.Schema(type=openapi.TYPE_STRING, description='数据值（单条时必填）'),
                'data_list': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'word_code': openapi.Schema(type=openapi.TYPE_STRING, description='词条编号'),
                            'check_time': openapi.Schema(type=openapi.TYPE_STRING, description='检查时间'),
                            'value': openapi.Schema(type=openapi.TYPE_STRING, description='数据值'),
                        }
                    ),
                    description='批量数据列表（批量时必填）'
                ),
            },
            required=['case_code', 'template_code'],
            example={
                'case_code': 'C000001',
                'template_code': 'T000001',
                'data_list': [
                    {'word_code': 'A000001', 'check_time': '2025-05-25 14:30:00', 'value': '值1'},
                    {'word_code': 'A000002', 'check_time': '2025-05-25 15:30:00', 'value': '值2'}
                ]
            }
        ),
        responses={
            200: openapi.Response(
                description="成功创建数据（单条或批量）",
                examples={
                    "application/json": {
                        "code": 200,
                        "msg": "创建成功",
                        "data": {
                            "message": "成功创建 2 条数据记录",
                            "data": [
                                {
                                    "id": 123,
                                    "case_code": "C000001",
                                    "template_category": "分类1",
                                    "template_name": "测试",
                                    "word_name": "string",
                                    "value": "值1",
                                    "check_time": "2025-05-25 14:30:00"
                                },
                                {
                                    "id": 124,
                                    "case_code": "C000001",
                                    "template_category": "分类1",
                                    "template_name": "测试",
                                    "word_name": "string",
                                    "value": "值2",
                                    "check_time": "2025-05-25 15:30:00"
                                }
                            ]
                        }
                    }
                }
            ),
            400: '参数错误',
            409: '数据已存在'
        }
    )
    def post(self, request):
        """创建数据，支持单条和批量（data_list）"""
        # 判断是否为批量
        if request.data.get('data_list'):
            # 批量模式
            serializer = DataTableBulkCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instances = serializer.save()
            return Response({
                'code': 200,
                'msg': '创建成功',
                'data': serializer.data
            })
        # 单条模式（原有逻辑）
        case_code = request.data.get('case_code')
        template_code = request.data.get('template_code')
        word_code = request.data.get('word_code')
        check_time = request.data.get('check_time')
        value = request.data.get('value')
        
        if not all([case_code, template_code, word_code, check_time, value]):
            return Response({
                'code': 400,
                'msg': '请提供case_code、template_code、word_code、check_time和value',
                'data': None
            }, status=400)

        from .models import Case, DataTemplate, Dictionary, DataTable
        from django.utils.dateparse import parse_datetime
        
        try:
            case = Case.objects.get(case_code=case_code)
            template = DataTemplate.objects.get(template_code=template_code)
            dictionary = Dictionary.objects.get(word_code=word_code)
            dt_check_time = parse_datetime(check_time)
            if not dt_check_time:
                raise ValueError("时间格式错误")
        except (Case.DoesNotExist, DataTemplate.DoesNotExist, Dictionary.DoesNotExist, ValueError) as e:
            return Response({
                'code': 404,
                'msg': f'未找到相关数据: {str(e)}',
                'data': None
            }, status=404)

        # 检查是否已存在
        if DataTable.objects.filter(
            case=case,
            data_template=template,
            dictionary=dictionary,
            check_time=dt_check_time
        ).exists():
            return Response({
                'code': 409,
                'msg': '数据已存在',
                'data': None
            }, status=409)

        # 创建新数据
        data_table = DataTable.objects.create(
            case=case,
            data_template=template,
            dictionary=dictionary,
            check_time=dt_check_time,
            value=value
        )

        return Response({
            'code': 200,
            'msg': '创建成功',
            'data': {
                'id': data_table.id,
                'case_code': case_code,
                'template_code': template_code,
                'word_code': word_code,
                'word_name': dictionary.word_name,
                'value': value,
                'check_time': check_time
            }
        })

    @swagger_auto_schema(
        operation_description="更新数据",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['case_code', 'template_code', 'word_code', 'check_time', 'value'],
            properties={
                'case_code': openapi.Schema(type=openapi.TYPE_STRING, description='病例编号'),
                'template_code': openapi.Schema(type=openapi.TYPE_STRING, description='模板编号'),
                'word_code': openapi.Schema(type=openapi.TYPE_STRING, description='词条编号'),
                'check_time': openapi.Schema(type=openapi.TYPE_STRING, description='检查时间，格式YYYY-MM-DD HH:MM:SS'),
                'value': openapi.Schema(type=openapi.TYPE_STRING, description='新的数据值'),
            },
            example={
                'case_code': 'C000001',
                'template_code': 'T000001',
                'word_code': 'A000001',
                'check_time': '2025-06-18 04:36:00',
                'value': '6.1'
            }
        ),
        responses={
            200: openapi.Response(
                description="成功更新数据",
                examples={
                    "application/json": {
                        "code": 200,
                        "msg": "更新成功",
                        "data": {
                            "id": 123,
                            "case_code": "C000001",
                            "template_code": "T000001",
                            "word_code": "A000001",
                            "word_name": "白细胞",
                            "value": "6.1",
                            "check_time": "2025-06-18 04:36:00"
                        }
                    }
                }
            ),
            400: '参数错误',
            404: '未找到相关数据'
        }
    )
    def put(self, request):
        """更新数据"""
        case_code = request.data.get('case_code')
        template_code = request.data.get('template_code')
        word_code = request.data.get('word_code')
        check_time = request.data.get('check_time')
        value = request.data.get('value')
        
        if not all([case_code, template_code, word_code, check_time, value]):
            return Response({
                'code': 400,
                'msg': '请提供case_code、template_code、word_code、check_time和value',
                'data': None
            }, status=400)

        from .models import Case, DataTemplate, Dictionary, DataTable
        from django.utils.dateparse import parse_datetime
        
        try:
            case = Case.objects.get(case_code=case_code)
            template = DataTemplate.objects.get(template_code=template_code)
            dictionary = Dictionary.objects.get(word_code=word_code)
            dt_check_time = parse_datetime(check_time)
            if not dt_check_time:
                raise ValueError("时间格式错误")
        except (Case.DoesNotExist, DataTemplate.DoesNotExist, Dictionary.DoesNotExist, ValueError) as e:
            return Response({
                'code': 404,
                'msg': f'未找到相关数据: {str(e)}',
                'data': None
            }, status=404)

        try:
            data_table = DataTable.objects.get(
                case=case,
                data_template=template,
                dictionary=dictionary,
                check_time=dt_check_time
            )
        except DataTable.DoesNotExist:
            return Response({
                'code': 404,
                'msg': '未找到相关数据',
                'data': None
            }, status=404)

        # 更新数据
        data_table.value = value
        data_table.save()

        return Response({
            'code': 200,
            'msg': '更新成功',
            'data': {
                'id': data_table.id,
                'case_code': case_code,
                'template_code': template_code,
                'word_code': word_code,
                'word_name': dictionary.word_name,
                'value': value,
                'check_time': check_time
            }
        })

    @swagger_auto_schema(
        operation_description="删除数据",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['case_code', 'template_code', 'word_code', 'check_time'],
            properties={
                'case_code': openapi.Schema(type=openapi.TYPE_STRING, description='病例编号'),
                'template_code': openapi.Schema(type=openapi.TYPE_STRING, description='模板编号'),
                'word_code': openapi.Schema(type=openapi.TYPE_STRING, description='词条编号'),
                'check_time': openapi.Schema(type=openapi.TYPE_STRING, description='检查时间，格式YYYY-MM-DD HH:MM:SS'),
            },
            example={
                'case_code': 'C000001',
                'template_code': 'T000001',
                'word_code': 'A000001',
                'check_time': '2025-06-18 04:36:00'
            }
        ),
        responses={
            200: openapi.Response(
                description="成功删除数据",
                examples={
                    "application/json": {
                        "code": 200,
                        "msg": "删除成功",
                        "data": None
                    }
                }
            ),
            400: '参数错误',
            404: '未找到相关数据'
        }
    )
    def delete(self, request):
        """删除数据"""
        case_code = request.data.get('case_code')
        template_code = request.data.get('template_code')
        word_code = request.data.get('word_code')
        check_time = request.data.get('check_time')
        
        if not all([case_code, template_code, word_code, check_time]):
            return Response({
                'code': 400,
                'msg': '请提供case_code、template_code、word_code和check_time',
                'data': None
            }, status=400)

        from .models import Case, DataTemplate, Dictionary, DataTable
        from django.utils.dateparse import parse_datetime
        
        try:
            case = Case.objects.get(case_code=case_code)
            template = DataTemplate.objects.get(template_code=template_code)
            dictionary = Dictionary.objects.get(word_code=word_code)
            dt_check_time = parse_datetime(check_time)
            if not dt_check_time:
                raise ValueError("时间格式错误")
        except (Case.DoesNotExist, DataTemplate.DoesNotExist, Dictionary.DoesNotExist, ValueError) as e:
            return Response({
                'code': 404,
                'msg': f'未找到相关数据: {str(e)}',
                'data': None
            }, status=404)

        try:
            data_table = DataTable.objects.get(
                case=case,
                data_template=template,
                dictionary=dictionary,
                check_time=dt_check_time
            )
        except DataTable.DoesNotExist:
            return Response({
                'code': 404,
                'msg': '未找到相关数据',
                'data': None
            }, status=404)

        # 删除数据
        data_table.delete()

        return Response({
            'code': 200,
            'msg': '删除成功',
            'data': None
        })