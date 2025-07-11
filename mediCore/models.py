from django.db import models

# 性别映射
GENDER_CHOICES = [
    (0, '女'),
    (1, '男'),
]
# 系统词条
class Dictionary(models.Model):
    id = models.AutoField(primary_key=True, help_text='词条id')
    word_code = models.CharField(max_length=255, unique=True, help_text='词条编号')
    word_name = models.CharField(max_length=255, db_index=True, help_text='中文名称')
    word_eng = models.CharField(max_length=255, null=True, blank=True, help_text='英文名称')
    word_short = models.CharField(max_length=255, null=True, blank=True, help_text='英文缩写')
    word_class = models.CharField(max_length=255, help_text='词条类型')
    word_apply = models.CharField(max_length=255, help_text='词条应用')
    word_belong = models.CharField(max_length=255, null=True, blank=True, help_text='从属别名')
    data_type = models.CharField(max_length=128, null=True, blank=True, help_text='数据类型，如数值类型、文本类型')
    input_type = models.CharField(
        max_length=32,
        choices=[
            ('single', '单选'),
            ('multi', '多选'),
            ('text', '填空'),
            ('date', '日期'),
            ('single_with_other', '单选+其他项'),
            ('single_with_date', '单选+日期'),
            ('multi_with_date', '多选+日期'),
            ('multi_with_text', '多选+填空'),
            ('hierarchical_select', '多级选择'),
        ],
        null=True,
        blank=True,
        default='text',
        verbose_name='填写方式'
    )
    options = models.TextField(blank=True, null=True, verbose_name='主选项')
    followup_options = models.JSONField(blank=True, null=True, verbose_name='后续选项')
    has_unit = models.BooleanField(default=False, help_text='是否有单位 0-无 1-有')
    unit = models.CharField(max_length=32, null=True, blank=True, help_text='词条单位')
    is_score = models.BooleanField(default=False, help_text='是否为评分词条 0-不是 1-是')
    score_func = models.TextField(null=True, blank=True, help_text='评分计算方式')

    class Meta:
        db_table = 'dictionary'
        verbose_name = '系统词条'
        verbose_name_plural = '系统词条表'

    def __str__(self):
        return f"{self.word_name} ({self.word_code})"

# 数据模板分类
class DataTemplateCategory(models.Model):
    id = models.AutoField(primary_key=True, help_text='模板分类id')
    name = models.CharField(max_length=255, help_text='模板分类名称')

    class Meta:
        db_table = 'data_template_category'
        verbose_name = '数据模板分类'
        verbose_name_plural = '数据模板分类表'

    def __str__(self):
        return self.name

# 数据模板
class DataTemplate(models.Model):
    id = models.AutoField(primary_key=True, help_text='数据模板id')
    template_code = models.CharField(max_length=255, unique=True, help_text='模板编号')
    template_name = models.CharField(max_length=255, help_text='模板名称')
    template_description = models.TextField(null=True, blank=True, help_text='模板描述')
    category = models.ForeignKey(
        DataTemplateCategory,
        on_delete=models.CASCADE,
        db_column='category_id',
        help_text='模板分类id'
    )
    # 数据模板-系统词条 多对多关系
    dictionaries = models.ManyToManyField(
        Dictionary,
        through='DataTemplateDictionary',
        related_name='data_templates'
    )

    class Meta:
        db_table = 'data_template'
        verbose_name = '数据模板'
        verbose_name_plural = verbose_name
        ordering = ['template_code']

    def __str__(self):
        return f"{self.template_name} ({self.template_code})"


# 数据模板-系统词条 多对多关系
class DataTemplateDictionary(models.Model):
    id = models.AutoField(primary_key=True, help_text='自增id')
    data_template = models.ForeignKey(
        DataTemplate,
        on_delete=models.CASCADE,
        db_column='data_template_id',
        help_text='数据模板id'
    )
    dictionary = models.ForeignKey(
        Dictionary,
        on_delete=models.CASCADE,
        db_column='dictionary_id',
        help_text='词条id'
    )

    class Meta:
        db_table = 'data_template_dictionary'
        verbose_name = '模板词条关系'
        verbose_name_plural = verbose_name
        unique_together = ('data_template', 'dictionary')  # 防止重复添加词条

    def __str__(self):
        return f"{self.data_template.template_name} - {self.dictionary.word_name}"


# 患者
class Identity(models.Model):
    identity_id = models.CharField(primary_key=True, max_length=255, help_text='身份证号')
    name = models.CharField(max_length=255, help_text='姓名')
    gender = models.PositiveSmallIntegerField(choices=GENDER_CHOICES, help_text='性别 0-女 1-男')
    birth_date = models.DateField(help_text='出生年月日')

    class Meta:
        db_table = 'identity'
        verbose_name = '患者身份'
        verbose_name_plural = '患者表'

    def __str__(self):
        return f"{self.name} ({self.identity_id})"

# 病例
class Case(models.Model):
    id = models.AutoField(primary_key=True, help_text='病例id')
    case_code = models.CharField(max_length=255, unique=True, help_text='病例编号')
    identity = models.ForeignKey(
        Identity,
        on_delete=models.CASCADE,
        db_column='identity_id',
        to_field='identity_id',
        help_text='身份证号'
    )
    opd_id = models.CharField(max_length=255, null=True, blank=True, help_text='门诊号')
    inhospital_id = models.CharField(max_length=255, null=True, blank=True, help_text='住院号')
    name = models.CharField(max_length=255, help_text='姓名')
    gender = models.PositiveSmallIntegerField(choices=GENDER_CHOICES, help_text='性别 0-女 1-男')
    birth_date = models.DateField(help_text='出生年月日')
    phone_number = models.CharField(max_length=36, null=True, blank=True, help_text='联系电话')
    home_address = models.CharField(max_length=512, null=True, blank=True, help_text='家庭住址')
    blood_type = models.CharField(max_length=10, null=True, blank=True, help_text='血型')
    main_diagnosis = models.CharField(max_length=1024, null=True, blank=True, help_text='主要诊断')
    has_transplant_surgery = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        default='未填写',
        help_text='是否行移植手术,示例 是(2025-5-27)'
    )
    is_in_transplant_queue = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        default='未填写',
        help_text='是否存在移植排队'
    )

    # ManyToMany relationship with Archive through ArchiveCase
    archives = models.ManyToManyField(
        'Archive', # Use string if Archive is defined later
        through='ArchiveCase',
        related_name='cases'
    )

    class Meta:
        db_table = 'case' # Explicitly set table name because 'case' is a reserved word in some SQL dbs
        verbose_name = '病例'
        verbose_name_plural = '病例表'
        indexes = [
            models.Index(fields=['identity'], name='idx_identity_id_on_case'), # Corresponds to INDEX `idx_identity_id`
        ]

    def __str__(self):
        return f"病例: {self.case_code} - {self.name}"

class DataTable(models.Model):
    id = models.AutoField(primary_key=True, help_text='自增id')
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        db_column='case_id',
        help_text='病例id'
    )
    data_template = models.ForeignKey(
        DataTemplate,
        on_delete=models.CASCADE,
        db_column='data_template_id',
        help_text='数据模板id'
    )
    dictionary = models.ForeignKey(
        Dictionary,
        on_delete=models.CASCADE,
        db_column='dictionary_id',
        help_text='词条id'
    )
    value = models.JSONField(help_text='值') # Consider TextField if values can be very long
    check_time = models.DateTimeField(help_text='检查时间') # Changed to DateTimeField

    class Meta:
        db_table = 'data_table'
        unique_together = (('case', 'data_template', 'dictionary', 'check_time'),)
        verbose_name = '数据'
        verbose_name_plural = '数据表'

    def __str__(self):
        return f"Data for Case {self.case_id} - Template {self.data_template_id} - Dict {self.dictionary_id}: {self.value[:50]}"

class Archive(models.Model):
    id = models.AutoField(primary_key=True, help_text='档案id')
    archive_code = models.CharField(max_length=255, unique=True, help_text='档案编号')
    archive_name = models.CharField(max_length=255, help_text='档案名称')
    archive_description = models.TextField(null=True, blank=True, help_text='档案描述')

    class Meta:
        db_table = 'archive'
        verbose_name = '专病档案'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.archive_name} ({self.archive_code})"

    @property
    def case_count(self):
        """获取档案包含的病例数"""
        return self.cases.count()

class ArchiveCase(models.Model):
    id = models.AutoField(primary_key=True, help_text='自增主键')
    archive = models.ForeignKey(
        Archive,
        on_delete=models.CASCADE,
        db_column='archive_id',
        help_text='档案id'
    )
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        db_column='case_id',
        help_text='病例id'
    )

    class Meta:
        db_table = 'archive_case'
        unique_together = ('archive', 'case')
        verbose_name = '档案病例关联'
        verbose_name_plural = '档案与病例关联表'

    def __str__(self):
        return f"Archive: {self.archive.archive_name} - Case: {self.case.case_code}"

class Images(models.Model): # Singular model name
    id = models.AutoField(primary_key=True, help_text='自增主键')
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        db_column='case_id',
        related_name='images', # Allows case.images.all()
        help_text='病例id'
    )
    data_template = models.ForeignKey(
        DataTemplate,
        on_delete=models.CASCADE, # Or SET_NULL if image can exist without template
        db_column='data_template_id',
        related_name='images', # Allows template.images.all()
        help_text='数据模板id'
    )
    # For 'url', models.URLField might be more appropriate if it's always a URL.
    # If you plan to store files with Django, models.ImageField or models.FileField are better.
    # For now, CharField matches varchar(255).
    url = models.CharField(max_length=255, help_text='图片url')
    remark = models.CharField(max_length=255, null=True, blank=True, help_text='图片备注')

    class Meta:
        db_table = 'images'
        verbose_name = '图片'
        verbose_name_plural = '图片表'

    def __str__(self):
        return f"Image for Case {self.case_id} - Template {self.data_template_id} ({self.url})"