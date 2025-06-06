from utils.viewsets import CustomModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Prefetch
from rest_framework.viewsets import GenericViewSet
from rest_framework import mixins
from .models import Dictionary, DataTemplate, Archive, Case, Identity, DataTable
from .serializers import (
    DictionarySerializer, DataTemplateSerializer,
    ArchiveListSerializer, ArchiveDetailSerializer, ArchiveSerializer,
    CaseListSerializer, CaseDetailSerializer, CaseSerializer,
    IdentitySerializer, PatientDetailSerializer, DataTableDetailSerializer,
    DataTableSerializer, DataTableBulkCreateSerializer
)
from utils.pagination import StandardPagination

class DictionaryViewSet(CustomModelViewSet):
    """
    API endpoint for 系统词条 (System Dictionary).

    - **Create**: POST /api/dictionary/
      - `word_code` is auto-generated.
      - Required fields: `word_name`, `word_class`, `word_apply`.
      - Optional fields: `word_eng`, `word_short`, `word_belong`, `data_type`.
    - **List**: GET /api/dictionary/
      - 支持分页: ?page=1&page_size=10
    - **Retrieve**: GET /api/dictionary/{word_code}/
    - **Update**: PUT /api/dictionary/{word_code}/ (all fields except word_code)
    - **Partial Update**: PATCH /api/dictionary/{word_code}/ (specified fields except word_code)
    - **Delete**: DELETE /api/dictionary/{word_code}/
    """
    queryset = Dictionary.objects.all().order_by('word_code')
    serializer_class = DictionarySerializer
    lookup_field = 'word_code'
    pagination_class = StandardPagination

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
      - 支持搜索: ?search=xxx（可搜索：档案编号、身份证号、门诊号、住院号、姓名）
    
    - **Retrieve**: GET /api/case/{case_code}/
      - 返回病例详细信息，包括关联的档案
    
    - **Update**: PUT /api/case/{case_code}/
      - 可更新除case_code外的所有字段
    
    - **Delete**: DELETE /api/case/{case_code}/
    
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
      - 支持分页和搜索：?search=xxx（可搜索：身份证号、姓名）
    
    - **Retrieve**: GET /api/patient/{identity_id}/
      - 返回患者详情及其所有病例
    
    - **Update**: PUT /api/patient/{identity_id}/
      - 可更新患者的基本信息
    """
    queryset = Identity.objects.all()
    serializer_class = IdentitySerializer
    lookup_field = 'identity_id'
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            return queryset.filter(
                Q(identity_id__icontains=search) |
                Q(name__icontains=search)
            )
        return queryset

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
    ```json
    {
        "case_code": "C000001",        // 病例编号
        "template_code": "T000001",    // 模板编号
        "word_code": "A000001",        // 词条编号
        "check_time": "2025-05-25",    // 检查时间，格式：YYYY-MM-DD
        "value": "检查值"              // 数据值
    }
    ```

    ### 2. 批量数据录入
    POST /api/data/
    ```json
    {
        "case_code": "C000001",        // 病例编号
        "template_code": "T000001",    // 模板编号
        "data_list": [
            {
                "word_code": "A000001",     // 词条编号
                "check_time": "2025-05-25", // 检查时间
                "value": "值1"              // 数据值
            },
            {
                "word_code": "A000002",
                "check_time": "2025-05-25",
                "value": "值2"
            }
        ]
    }
    ```
      ### 3. 数据列表查询
    GET /api/data/[?page=1&page_size=10][&case_code=C000001]
    
    响应格式：
    ```json
    {
        "code": 200,                    // 状态码
        "msg": "操作成功",              // 响应消息
        "data": {
            "list": [                   // 数据列表
                {
                    "id": 1,
                    "case_code": "C000001",
                    "template_category": "分类1",
                    "template_name": "测试",
                    "word_name": "string",
                    "value": "检查值",
                    "check_time": "2025-05-25T00:00:00"
                }
            ],
            "total": 4,                // 总记录数
            "page": 1,                 // 当前页码
            "page_size": 10            // 每页记录数
        }
    }
    ```
      ### 4. 查询单条数据详情
    GET /api/data/{id}/
    
    响应格式：
    ```json
    {
        "code": 200,
        "msg": "操作成功",
        "data": {
            "id": 1,
            "case_code": "C000001",
            "template_category": "分类1",
            "template_name": "测试",
            "word_name": "string",
            "value": "检查值",
            "check_time": "2025-05-25T00:00:00"
        }
    }
    ```

    ## 错误响应示例
    ```json
    {
        "code": 400,
        "msg": "请求参数错误",
        "data": {
            "case_code": ["病例编号不存在"],
            "template_code": ["模板编号不存在"],
            "word_code": ["词条编号不存在"],
            "check_time": ["日期格式错误: xxx, 应为YYYY-MM-DD格式"]
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