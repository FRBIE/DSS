CREATE DATABASE IF NOT EXISTS medical_data;


CREATE USER IF NOT EXISTS 'mediCore'@'%' IDENTIFIED BY 'bWVkaUNvcmU=';
GRANT ALL PRIVILEGES ON medical_data.* TO 'mediCore'@'%';
FLUSH PRIVILEGES;

USE medical_data;
--  DDL
CREATE TABLE `dictionary`  (
  `id` int  NOT NULL AUTO_INCREMENT COMMENT '词条id',
  `word_code` varchar(255) NOT NULL COMMENT '词条编号',
  `word_name` varchar(255) NOT NULL COMMENT '中文名称',
  `word_eng` varchar(255) NULL COMMENT '英文名称',
  `word_short` varchar(255) NULL COMMENT '英文缩写',
  `word_class` varchar(255) NOT NULL COMMENT '词条类型',
  `word_apply` varchar(255) NOT NULL COMMENT '词条应用',
  `word_belong` varchar(255) NULL COMMENT '从属别名',
  `data_type` varchar(128) null comment '数据类型，如数值类型、文本类型',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uk_word_code` (`word_code`), -- 确保 word_code 的唯一性
  INDEX `name_index`(`word_name`)
 )COMMENT='系统词条表';


CREATE TABLE `data_template`  (
  `id` int  NOT NULL AUTO_INCREMENT COMMENT '数据模板id',
  `template_code` varchar(255) NOT NULL COMMENT '模板编号',
  `template_name` varchar(255) NOT NULL COMMENT '模板名称',
  `template_description` text NULL COMMENT '模板描述',
  `category_id` int NOT NULL COMMENT '模板分类id',
  PRIMARY KEY (`id`),
   UNIQUE INDEX `uk_template_code` (`template_code`), -- 确保唯一性
)COMMENT='数据模板表';


CREATE TABLE `data_template_category`  (
  `id` int NOT NULL COMMENT '模板分类id',
  `name` varchar(255) NOT NULL COMMENT '模板分类名称',
  PRIMARY KEY (`id`)
)COMMENT='数据模板分类表';


CREATE TABLE `data_template_dictionary` (
  `id` INT  NOT NULL AUTO_INCREMENT COMMENT '自增id',
  `data_template_id` INT  NOT NULL COMMENT '数据模板id',
  `dictionary_id` INT  NOT NULL COMMENT '词条id',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_template_dictionary` (`data_template_id`, `dictionary_id`), -- 唯一约束，确保一个模板中一个词条只出现一次
) COMMENT='数据模板与词条关联表';


CREATE TABLE `data_table`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增id',
  `case_id` int NOT NULL COMMENT '病例id',
  `data_template_id` int NOT NULL COMMENT '数据模板id',
  `dictionary_id` int not null comment '词条id'
  `value` varchar(1024) NOT NULL COMMENT '值',
  `check_time` datetime not null comment '检查时间'
  PRIMARY KEY (`id`),
   UNIQUE INDEX `uk_data` (`case_id`, `data_template_id`,`dictionary_id`), -- 确保唯一性
)COMMENT='数据表';


CREATE TABLE `case`  (
  `id` int NOT NULL COMMENT '病例id',
  `case_code` varchar(255) NOT NULL COMMENT '病例编号',
  `identity_id` varchar(255) NOT NULL COMMENT '身份证号',
  `opd_id` varchar(255) NULL COMMENT '门诊号',
  `inhospital_id` varchar(255) NULL COMMENT '住院号',
  `name` varchar(255) NOT NULL COMMENT '姓名',
  `gender` tinyint(1) NOT NULL COMMENT '性别 0-女 1-男',
  `birth_date` datetime NOT NULL COMMENT '出生年月日',
  `phone_number` varchar(36) NULL COMMENT '联系电话',
  `home_address` varchar(512) NULL COMMENT '家庭住址',
  `blood_type` varchar(10) NULL COMMENT '血型',
  `main_diagnosis` varchar(1024) NULL COMMENT '主要诊断',
  `has_transplant_surgery` varchar(255) NULL DEFAULT '未填写' COMMENT  '是否行移植手术,示例 是(2025-5-27)',
  `is_in_transplant_queue` varchar(16) NULL DEFAULT '未填写' COMMENT '是否存在移植排队',
  PRIMARY KEY (`id`),
    UNIQUE INDEX `uk_case_code` (`case_code`), -- 确保唯一性
  INDEX `idx_identity_id` (`identity_id`), -- 身份证号索引
)COMMENT='病例表';

CREATE TABLE `archive`  (
  `id` int NOT NULL COMMENT '档案id',
  `archive_code` varchar(255) NOT NULL COMMENT '档案编号',
  `archive_name` varchar(255) NOT NULL COMMENT '档案名称',
  `archive_description` text NULL COMMENT '档案描述',
  PRIMARY KEY (`id`)
    UNIQUE INDEX `uk_data` (`archive_code`), -- 确保唯一性
)COMMENT='档案表';

CREATE TABLE `archive_case`  (
  `id` INT  NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `archive_id` int NOT NULL COMMENT '档案id',
  `case_id` int NOT NULL COMMENT '病例id',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_archive_case` (`archive_id`, `case_id`), -- 唯一约束，确保一个档案中一个病例只出现一次
)COMMENT='档案与病例关联表';

CREATE TABLE `identity`  (
  `identity_id` varchar(255) NOT NULL COMMENT '身份证号',
  `name` varchar(255) NOT NULL COMMENT '姓名',
  `gender` tinyint(1) NOT NULL COMMENT '性别 0-女 1-男',
  `birth_date` datetime NOT NULL COMMENT '出生年月日',
  PRIMARY KEY (`identity_id`),
  UNIQUE INDEX `identity_index`(`identity_id`)
)COMMENT='患者表';

CREATE TABLE `images`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `case_id` int NOT NULL COMMENT '病例id',
  `data_template_id` int NOT NULL COMMENT '数据模板id',
  `url` varchar(255) NOT  NULL comment '图片url',
  `remark` varchar(255) NULL comment '图片备注',
  PRIMARY KEY (`id`)
)COMMENT='图片表';