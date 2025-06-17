from django.contrib import admin
from django.urls import include
from django.urls import path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.views import RegisterView, LoginView
from .views import (
    DictionaryViewSet, DataTemplateViewSet, ArchiveViewSet, CaseViewSet,
    IdentityViewSet, DataTableViewSet, DataTemplateCategoryViewSet
)
from mediCore.views import PatientMergedCaseListView, CaseTemplateSummaryView, CaseTemplateDetailView, CaseVisualizationOptionsView, CaseVisualizationDataView

# 创建路由
router = DefaultRouter()
router.register(r'dictionary', DictionaryViewSet, basename='dictionary')
router.register(r'template-category', DataTemplateCategoryViewSet, basename='template-category')
router.register(r'data-template', DataTemplateViewSet, basename='data-template')
router.register(r'archive', ArchiveViewSet, basename='archive')
router.register(r'case', CaseViewSet, basename='case')
router.register(r'patient', IdentityViewSet, basename='patient')
router.register(r'data', DataTableViewSet, basename='data')

# Swagger文档配置
schema_view = get_schema_view(
    openapi.Info(
        title="MediCore API",
        default_version='v1',
        description="MediCore 系统API文档",
        terms_of_service="https://www.yourapp.com/terms/",
        contact=openapi.Contact(email="contact@yourapp.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

api_patterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_patterns)),
    path('api/', include(router.urls)),

    # Swagger文档
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    path('api/patient-merged-case/', PatientMergedCaseListView.as_view(), name='patient-merged-case'),
    path('api/case-template-summary/', CaseTemplateSummaryView.as_view(), name='case-template-summary'),
    path('api/case-template-detail/', CaseTemplateDetailView.as_view(), name='case-template-detail'),
    path('api/case-visualization-options/', CaseVisualizationOptionsView.as_view(), name='case-visualization-options'),
    path('api/case-visualization-data/', CaseVisualizationDataView.as_view(), name='case-visualization-data'),
]