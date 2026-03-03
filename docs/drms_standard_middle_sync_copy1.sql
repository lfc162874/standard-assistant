/*
 Navicat Premium Data Transfer

 Source Server         : 校验任务数据库
 Source Server Type    : MySQL
 Source Server Version : 80037 (8.0.37)
 Source Host           : 192.168.112.56:33306
 Source Schema         : source_wash_result

 Target Server Type    : MySQL
 Target Server Version : 80037 (8.0.37)
 File Encoding         : 65001

 Date: 28/02/2026 13:55:47
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for drms_standard_middle_sync_copy1
-- ----------------------------
DROP TABLE IF EXISTS `drms_standard_middle_sync`;
CREATE TABLE `drms_standard_middle_sync`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `a000` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '标准状态',
  `a001` bigint NULL DEFAULT NULL COMMENT '标准唯一标识（业务类表关联关系用）',
  `a001s` bigint NULL DEFAULT NULL COMMENT '标准唯一标识（基础信息关联关系用）',
  `a003` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '更新日期',
  `a100` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '标准号',
  `a100sim` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '标准号（简写）',
  `a101` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '发布日期',
  `a104` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '发布单位',
  `a104cn` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '发布单位中文名称',
  `a200` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '标准状态（细分状态）',
  `a203` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '有效区域',
  `a205` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '实施日期',
  `a206` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '作废日期',
  `a207` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '确认日期',
  `a209` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '起草单位',
  `a298` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '标准名称',
  `a300` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '语种',
  `a301` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '原文题名',
  `a302` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '英文题名',
  `a305` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '开本/页码（字段作废）',
  `a330` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '文摘适用范围',
  `a461` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '代替标准',
  `a462` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '被代替标准',
  `a502` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '引用标准',
  `a505` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '相关法律（字段作废）',
  `a800` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '采标情况(一致性)',
  `a825` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '中国标准分类号',
  `a825cn` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '中国标准分类号（中）',
  `cn1` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `cn2` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `cn3` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `cname1` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `cname2` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `cname3` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `csname1` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `csname2` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `csname3` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `a826` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '国际标准分类号',
  `a826cn` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '国际标准分类号（中）',
  `icsn1` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `icsn2` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `icsn3` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `icname1` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `icname2` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `icname3` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `icsname1` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `icsname2` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `icsname3` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `a835` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '中文主题词',
  `a835key` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '中文主题词（字段作废）',
  `a836` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '中文主题词（字段作废）',
  `a838` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '原文主题词',
  `a837` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '英文主题词',
  `a847` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '排序码',
  `a850` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '标准类型',
  `a863` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '文献代号',
  `a870` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '提出单位',
  `a871` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '归口单位',
  `a885` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '国别代号（区分国家）',
  `a885cn` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '国别中文',
  `A866` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '密级（字段作废）',
  `pdfname` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'PDF文件名',
  `pdf_path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'pdf存储相对路径',
  `jsonname` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'json文件名称',
  `worldname` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'word文件名称',
  `personofdraft` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '起草人 ',
  `sub_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '标准类型',
  `subtypedes` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '标准类型中文',
  `subtypeforce` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '强标/推标',
  `domain` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '国内/国外',
  `domaindes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '国内/国外中文描述',
  `issuer` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '标准号拆分的第一段',
  `stannum` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '标准号拆分的第二段',
  `yearnum` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '标准号拆分的第三段',
  `sortno` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'issuer的排序码',
  `pagenumber` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL COMMENT '页数',
  `data_source` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT '数据来源',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` bit(1) NOT NULL DEFAULT b'0' COMMENT '是否删除',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `a001`(`a001` ASC) USING BTREE,
  INDEX `a104`(`a104` ASC) USING BTREE,
  INDEX `a101`(`a101` ASC) USING BTREE,
  INDEX `a205`(`a205` ASC) USING BTREE,
  INDEX `a206`(`a206` ASC) USING BTREE,
  INDEX `a825`(`a825` ASC) USING BTREE,
  INDEX `a826`(`a826` ASC) USING BTREE,
  INDEX `a100`(`a100` ASC) USING BTREE,
  INDEX `a825cn`(`a825cn` ASC) USING BTREE,
  INDEX `a825cn_2`(`a825cn` ASC) USING BTREE,
  INDEX `a825cn_3`(`a825cn` ASC) USING BTREE,
  INDEX `drms_standard_sub_type_index`(`sub_type` ASC) USING BTREE,
  INDEX `subtypedes`(`subtypedes` ASC) USING BTREE,
  INDEX `yearnum`(`yearnum` ASC) USING BTREE,
  INDEX `pdfname`(`pdfname` ASC) USING BTREE,
  INDEX `a000`(`a000` ASC) USING BTREE,
  INDEX `a885cn`(`a885cn` ASC) USING BTREE,
  INDEX `idx_update_time`(`update_time` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 9999996457466650 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
