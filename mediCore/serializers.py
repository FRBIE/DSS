from rest_framework import serializers
from .models import (
    Dictionary, DataTemplateCategory, DataTemplate, DataTemplateDictionary,
    Identity, Case, Archive, ArchiveCase, DataTable, Images
)

from rest_framework import serializers
from django.db import IntegrityError, transaction
from django.utils.timezone import make_aware, get_current_timezone
from datetime import datetime
import re
import logging
import csv
import codecs
WORD_CLASS_TO_PREFIX_MAP = {
    "数据类型": "C",
    "字典词条": "A",
    "模板类别": "T",
    "临床信息": "I",
    "信息类型": "G",
    "检验类型": "E",
    "信息名称": "INF",
    "检验名称": "TES",
    "检查名称": "CHK",
    "检查类型": "EX",
}


class DictionarySerializer(serializers.ModelSerializer):
    word_code = serializers.CharField(read_only=True, help_text='词条编号 (自动生成)')

    class Meta:
        model = Dictionary
        fields = [
            'id',
            'word_code',
            'word_name',
            'word_eng',
            'word_short',
            'word_class',
            'word_apply',
            'word_belong',
            'data_type'
        ]
        read_only_fields = ['id']  # 添加id为只读字段

    def validate_word_class(self, value):
        """
        Validate if the provided word_class is known.
        """
        if value not in WORD_CLASS_TO_PREFIX_MAP:
            raise serializers.ValidationError(
                f"未知的词条类型: '{value}'. 可用类型: {', '.join(WORD_CLASS_TO_PREFIX_MAP.keys())}"
            )
        return value

    def create(self, validated_data):
        word_class = validated_data.get('word_class')
        prefix = WORD_CLASS_TO_PREFIX_MAP.get(word_class)

        if not prefix:
            raise serializers.ValidationError({"word_class": "无法根据词条类型生成编号前缀."})

        last_entry = Dictionary.objects.filter(word_code__startswith=prefix).order_by('-word_code').first()

        next_numeric_part = 1
        if last_entry and last_entry.word_code:
            numeric_str_match = re.search(r'\d+$', last_entry.word_code)
            if numeric_str_match:
                try:
                    next_numeric_part = int(numeric_str_match.group(0)) + 1
                except ValueError:
                    pass

        NUM_DIGITS = 6
        generated_word_code = f"{prefix}{next_numeric_part:0{NUM_DIGITS}d}"
        validated_data['word_code'] = generated_word_code
        try:
            instance = super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({
                "word_code": "无法生成唯一的词条编号，请重试。"
            })
        return instance

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class DataTemplateCategorySerializer(serializers.ModelSerializer):
    """数据模板分类序列化器"""
    template_count = serializers.SerializerMethodField(help_text='该分类下的模板数量')
    
    class Meta:
        model = DataTemplateCategory
        fields = ['id', 'name', 'template_count']
        read_only_fields = ['id']  # 设置id为只读字段

    def get_template_count(self, obj):
        return obj.datatemplate_set.count()

    def validate_name(self, value):
        """验证分类名称的唯一性"""
        if self.instance:  # 更新时排除自身
            exists = DataTemplateCategory.objects.exclude(id=self.instance.id).filter(name=value).exists()
        else:  # 创建时直接检查
            exists = DataTemplateCategory.objects.filter(name=value).exists()
        
        if exists:
            raise serializers.ValidationError('该分类名称已存在')
        return value


class DataTemplateSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    template_code = serializers.CharField(read_only=True, help_text='模板编号（自动生成）')
    dictionaries = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Dictionary.objects.all(),
        required=False,
        write_only=True
    )
    dictionary_list = DictionarySerializer(
        source='dictionaries',
        many=True,
        read_only=True
    )

    class Meta:
        model = DataTemplate
        fields = ['id', 'template_code', 'template_name', 'template_description',
                  'category', 'category_name', 'dictionaries', 'dictionary_list']
        read_only_fields = ['id']  # 添加id为只读字段

    def generate_template_code(self):
        """
        生成模板编号：T + 6位数字
        """
        prefix = 'T'
        NUM_DIGITS = 6
        last_template = DataTemplate.objects.filter(
            template_code__startswith=prefix
        ).order_by('-template_code').first()

        next_number = 1
        if last_template and last_template.template_code:
            numeric_part = last_template.template_code[len(prefix):]
            if numeric_part.isdigit():
                next_number = int(numeric_part) + 1

        return f"{prefix}{next_number:0{NUM_DIGITS}d}"

    def create(self, validated_data):
        dictionaries_data = validated_data.pop('dictionaries', [])
        validated_data['template_code'] = self.generate_template_code()

        try:
            template = DataTemplate.objects.create(**validated_data)
            if dictionaries_data:
                data_template_dictionaries = [
                    DataTemplateDictionary(data_template=template, dictionary=dictionary)
                    for dictionary in dictionaries_data
                ]
                DataTemplateDictionary.objects.bulk_create(data_template_dictionaries)

            return template
        except IntegrityError:
            raise serializers.ValidationError({
                "template_code": "无法生成唯一的模板编号，请重试。"
            })

    def update(self, instance, validated_data):
        dictionaries_data = validated_data.pop('dictionaries', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if dictionaries_data is not None:
            # 清除现有关联
            DataTemplateDictionary.objects.filter(data_template=instance).delete()
            # 创建新关联
            data_template_dictionaries = [
                DataTemplateDictionary(data_template=instance, dictionary=dictionary)
                for dictionary in dictionaries_data
            ]
            DataTemplateDictionary.objects.bulk_create(data_template_dictionaries)

        return instance


class DataTemplateDictionarySerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='data_template.template_name', read_only=True)
    word_name = serializers.CharField(source='dictionary.word_name', read_only=True)

    class Meta:
        model = DataTemplateDictionary
        fields = '__all__'


class BaseCaseSerializer(serializers.ModelSerializer):
    """病例序列化器的基类"""
    identity_name = serializers.CharField(source='identity.name', read_only=True)
    case_code = serializers.CharField(read_only=True, help_text='病例编号（自动生成）')
    archive_codes = serializers.SerializerMethodField(help_text='关联的档案编号列表')
    age = serializers.SerializerMethodField(help_text='年龄')

    def get_archive_codes(self, obj):
        return list(obj.archives.values_list('archive_code', flat=True))

    def get_age(self, obj):
        from datetime import date
        today = date.today()
        born = obj.birth_date
        return (today.year - born.year) - ((today.month, today.day) < (born.month, born.day))


class CaseListSerializer(BaseCaseSerializer):
    """用于病例列表的序列化器"""

    class Meta:
        model = Case
        fields = [
            'id', 'case_code', 'identity', 'identity_name', 'opd_id', 'inhospital_id',
            'name', 'gender', 'birth_date', 'phone_number', 'home_address',
            'blood_type', 'main_diagnosis', 'has_transplant_surgery',
            'is_in_transplant_queue', 'archive_codes', 'age'
        ]
        ref_name = 'CaseList'


class CaseDetailSerializer(BaseCaseSerializer):
    """用于病例详情的序列化器"""
    archives = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Archive.objects.all(),
        required=False,
        help_text='关联的档案列表'
    )

    class Meta:
        model = Case
        fields = [
            'id', 'case_code', 'identity', 'identity_name', 'opd_id', 'inhospital_id',
            'name', 'gender', 'birth_date', 'phone_number', 'home_address',
            'blood_type', 'main_diagnosis', 'has_transplant_surgery',
            'is_in_transplant_queue', 'archive_codes', 'archives', 'age'
        ]
        ref_name = 'CaseDetail'


class CaseSerializer(CaseDetailSerializer):
    """基础序列化器，包含通用的创建和更新逻辑"""
    identity = serializers.CharField(help_text='身份证号')  # 改为 CharField，接收身份证号字符串
    archive_codes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True,
        help_text='档案编号列表'
    )

    class Meta(CaseDetailSerializer.Meta):
        ref_name = 'Case'
        read_only_fields = ['id']  # 添加id为只读字段

    def validate_identity(self, value):
        """验证身份证号格式"""
        if not value or len(value) != 18:
            raise serializers.ValidationError("请提供有效的18位身份证号")
        return value

    def generate_case_code(self):
        """生成病例编号：C + 6位数字"""
        prefix = 'C'
        NUM_DIGITS = 6
        last_case = Case.objects.filter(
            case_code__startswith=prefix
        ).order_by('-case_code').first()

        next_number = 1
        if last_case and last_case.case_code:
            numeric_part = last_case.case_code[len(prefix):]
            if numeric_part.isdigit():
                next_number = int(numeric_part) + 1

        return f"{prefix}{next_number:0{NUM_DIGITS}d}"

    def validate_birth_date(self, value):
        """验证出生日期的格式"""
        from datetime import datetime, date

        if isinstance(value, date):
            return value
        elif isinstance(value, str):
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                raise serializers.ValidationError('日期格式错误，请使用YYYY-MM-DD格式')
        raise serializers.ValidationError('无效的日期格式')

    def validate_archive_codes(self, value):
        """验证档案编号列表"""
        if not value:
            return value

        archive_ids = []
        invalid_codes = []

        for archive_code in value:
            try:
                archive = Archive.objects.get(archive_code=archive_code)
                archive_ids.append(archive.id)
            except Archive.DoesNotExist:
                invalid_codes.append(archive_code)

        if invalid_codes:
            raise serializers.ValidationError(f"以下档案编号不存在: {', '.join(invalid_codes)}")

        return archive_ids

    def create(self, validated_data):
        logger = logging.getLogger(__name__)
        
        # 记录初始输入数据
        logger.info(f"开始创建病例，输入数据: {validated_data}")
        
        archives_data = validated_data.pop('archive_codes', [])
        archives_data = validated_data.pop('id', [])
        validated_data['case_code'] = self.generate_case_code()
        logger.info(f"生成的病例编号: {validated_data['case_code']}")

        # 处理患者信息
        identity_id = validated_data.pop('identity')  # 从验证后的数据中取出身份证号
        logger.info(f"处理患者信息，身份证号: {identity_id}")
        
        try:
            # 尝试获取已存在的患者
            identity = Identity.objects.get(identity_id=identity_id)
            logger.info(f"找到现有患者记录: {identity.name}")
            # 更新患者信息
            identity.name = validated_data.get('name')
            identity.gender = validated_data.get('gender')
            identity.birth_date = validated_data.get('birth_date')
            identity.save()
            logger.info("患者信息已更新")
        except Identity.DoesNotExist:
            # 创建新患者
            logger.info("未找到现有患者，创建新患者记录")
            identity = Identity.objects.create(
                identity_id=identity_id,
                name=validated_data.get('name'),
                gender=validated_data.get('gender'),
                birth_date=validated_data.get('birth_date')
            )
            logger.info(f"新患者创建成功: {identity.name}")

        # 添加身份证号回validated_data
        validated_data['identity'] = identity
        logger.info("准备创建病例记录")

        # 创建病例
        try:
            logger.debug(f"创建病例的数据: {validated_data}")
            case = Case.objects.create(**validated_data)
            logger.info(f"病例创建成功: {case.case_code}")
            
            if archives_data:
                logger.info(f"开始关联档案，档案ID列表: {archives_data}")
                archive_cases = [
                    ArchiveCase(case=case, archive_id=archive_id)
                    for archive_id in archives_data
                ]
                ArchiveCase.objects.bulk_create(archive_cases)
                logger.info("档案关联完成")
            return case
        except IntegrityError as e:
            logger.error(f"创建病例时发生完整性错误: {str(e)}")
            raise serializers.ValidationError({
                "case_code": "无法生成唯一的病例编号，请重试。"
            })

    def update(self, instance, validated_data):
        archives_data = validated_data.pop('archives', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if archives_data is not None:
            # 清除现有关联
            ArchiveCase.objects.filter(case=instance).delete()
            # 创建新关联
            archive_cases = [
                ArchiveCase(case=instance, archive=archive)
                for archive in archives_data
            ]
            ArchiveCase.objects.bulk_create(archive_cases)

        return instance


class IdentitySerializer(serializers.ModelSerializer):
    """用于患者基本信息的序列化器"""
    case_count = serializers.SerializerMethodField(help_text='关联的病例数')
    age = serializers.SerializerMethodField(help_text='年龄')

    class Meta:
        model = Identity
        fields = ['identity_id', 'name', 'gender', 'birth_date', 'case_count', 'age']
        read_only_fields = ['id']  # 添加id为只读字段

    def get_case_count(self, obj):
        return obj.case_set.count()

    def get_age(self, obj):
        from datetime import date
        today = date.today()
        born = obj.birth_date
        return (today.year - born.year) - ((today.month, today.day) < (born.month, born.day))


class PatientDetailSerializer(serializers.ModelSerializer):
    """用于患者详情的序列化器，包含病例信息"""
    case_list = CaseListSerializer(source='case_set', many=True, read_only=True)
    age = serializers.SerializerMethodField(help_text='年龄')

    class Meta:
        model = Identity
        fields = ['identity_id', 'name', 'gender', 'birth_date', 'age', 'case_list']
        read_only_fields = ['id']  # 添加id为只读字段

    def get_age(self, obj):
        from datetime import date
        today = date.today()
        born = obj.birth_date
        return (today.year - born.year) - ((today.month, today.day) < (born.month, born.day))


class DataTableDetailSerializer(serializers.ModelSerializer):
    """用于数据详情的序列化器"""
    case_code = serializers.CharField(source='case.case_code', read_only=True)
    template_name = serializers.CharField(source='data_template.template_name', read_only=True)
    template_category = serializers.CharField(source='data_template.category.name', read_only=True)
    word_name = serializers.CharField(source='dictionary.word_name', read_only=True)

    class Meta:
        model = DataTable
        fields = ['id', 'case_code', 'template_category', 'template_name',
                  'word_name', 'value', 'check_time']
        read_only_fields = ['id']  # 添加id为只读字段


class DataTableSerializer(serializers.ModelSerializer):
    """用于数据录入的序列化器"""
    case_code = serializers.CharField(write_only=True, help_text='病例编号')
    template_code = serializers.CharField(write_only=True, help_text='模板编号')
    word_code = serializers.CharField(write_only=True, help_text='词条编号')
    check_time = serializers.DateTimeField(help_text='检查时间')
    value = serializers.CharField(help_text='检查值')

    class Meta:
        model = DataTable
        fields = ['case_code', 'template_code', 'word_code', 'check_time', 'value']

    def create(self, validated_data):
        # 获取病例信息
        case_code = validated_data.pop('case_code')
        case = Case.objects.get(case_code=case_code)

        # 获取模板信息
        template_code = validated_data.pop('template_code')
        data_template = DataTemplate.objects.get(template_code=template_code)

        # 获取词条信息
        word_code = validated_data.pop('word_code')
        dictionary = Dictionary.objects.get(word_code=word_code)

        # 创建数据记录
        return DataTable.objects.create(
            case=case,
            data_template=data_template,
            dictionary=dictionary,
            **validated_data
        )

    def validate(self, data):
        try:
            Case.objects.get(case_code=data['case_code'])
        except Case.DoesNotExist:
            raise serializers.ValidationError({'case_code': '病例编号不存在'})

        try:
            DataTemplate.objects.get(template_code=data['template_code'])
        except DataTemplate.DoesNotExist:
            raise serializers.ValidationError({'template_code': '模板编号不存在'})

        try:
            Dictionary.objects.get(word_code=data['word_code'])
        except Dictionary.DoesNotExist:
            raise serializers.ValidationError({'word_code': '词条编号不存在'})

        return data


class ArchiveListSerializer(serializers.ModelSerializer):
    """用于档案列表的序列化器"""
    archive_code = serializers.CharField(read_only=True, help_text='档案编号（自动生成）')
    case_count = serializers.IntegerField(read_only=True, help_text='包含病例数')

    class Meta:
        model = Archive
        fields = ['id', 'archive_code', 'archive_name', 'case_count']
        read_only_fields = ['id']  # 添加id为只读字段

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['case_count'] = instance.cases.count()
        return data


class ArchiveDetailSerializer(serializers.ModelSerializer):
    """用于单个档案详情的序列化器"""
    archive_code = serializers.CharField(read_only=True, help_text='档案编号（自动生成）')
    archive_name = serializers.CharField(help_text='档案名称', default='string')
    archive_description = serializers.CharField(help_text='档案描述', default='string')
    case_list = CaseListSerializer(source='cases', many=True, read_only=True)

    class Meta:
        model = Archive
        fields = ['id', 'archive_code', 'archive_name', 'archive_description', 'case_list']
        ref_name = 'ArchiveDetail'


class ArchiveSerializer(ArchiveDetailSerializer):
    """基础序列化器，包含通用的创建和更新逻辑"""

    def generate_archive_code(self):
        """生成档案编号：A + 6位数字"""
        prefix = 'A'
        NUM_DIGITS = 6
        last_archive = Archive.objects.filter(
            archive_code__startswith=prefix
        ).order_by('-archive_code').first()

        next_number = 1
        if last_archive and last_archive.archive_code:
            numeric_part = last_archive.archive_code[len(prefix):]
            if numeric_part.isdigit():
                next_number = int(numeric_part) + 1

        return f"{prefix}{next_number:0{NUM_DIGITS}d}"

    def create(self, validated_data):
        validated_data['archive_code'] = self.generate_archive_code()
        try:
            return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError({
                "archive_code": "无法生成唯一的档案编号，请重试。"
            })


class DataTableBulkCreateSerializer(serializers.Serializer):
    """用于批量数据录入的序列化器"""
    case_code = serializers.CharField(help_text='病例编号')
    template_code = serializers.CharField(help_text='模板编号')
    data_list = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField(),
            allow_empty=False
        ),
        help_text='数据列表，每项包含word_code、value和check_time'
    )

    def validate(self, data):
        for item in data:
            try:
                datetime.strptime(item['check_time'], '%Y-%m-%d')
            except ValueError:
                raise serializers.ValidationError({
                    'check_time': f'日期格式错误: {item["check_time"]}, 请使用YYYY-MM-DD格式'
                })
        return data

    def create(self, validated_data):
        from django.db import transaction

        with transaction.atomic():
            records = []
            for item in validated_data['data_list']:
                dictionary = Dictionary.objects.get(word_code=item['word_code'])
                records.append(
                    DataTable(
                        case=self.case,
                        data_template=self.template,
                        dictionary=dictionary,
                        value=item['value'],
                        check_time=item['check_time']
                    )
                )
            return DataTable.objects.bulk_create(records)

    def to_representation(self, instance):
        # instance 是批量创建的记录列表
        return {
            'message': f'成功创建 {len(instance)} 条数据记录',
            'data': DataTableDetailSerializer(instance, many=True).data
        }


class DictionaryBulkImportSerializer(serializers.Serializer):
    """用于批量导入词条的序列化器"""
    file = serializers.FileField(help_text='CSV文件')

    def validate(self, attrs):
        file = attrs['file']
        if not file.name.endswith('.csv'):
            raise serializers.ValidationError("只支持CSV文件格式")
        return attrs

    def create(self, validated_data):
        file = validated_data['file']
        reader = csv.DictReader(codecs.iterdecode(file, 'utf-8'))
        
        # 验证CSV文件的列名
        required_fields = ['word_name', 'word_eng', 'word_short', 'word_class', 
                         'word_apply', 'word_belong', 'data_type']
        if not all(field in reader.fieldnames for field in required_fields):
            raise serializers.ValidationError("CSV文件格式不正确，请使用正确的模板")

        dictionaries = []
        errors = []
        
        for row in reader:
            try:
                # 过滤掉空字符串值，将其转换为None
                row = {k: (v if v.strip() != '' else None) for k, v in row.items()}
                
                # 创建词条
                dictionary = Dictionary.objects.create(
                    word_name=row['word_name'],
                    word_eng=row['word_eng'],
                    word_short=row['word_short'],
                    word_class=row['word_class'],
                    word_apply=row['word_apply'],
                    word_belong=row['word_belong'],
                    data_type=row['data_type']
                )
                dictionaries.append(dictionary)
            except Exception as e:
                errors.append(f"第{reader.line_num}行导入失败: {str(e)}")

        return {
            'success_count': len(dictionaries),
            'error_count': len(errors),
            'errors': errors
        }