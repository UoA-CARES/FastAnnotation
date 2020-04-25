CREATE DATABASE  IF NOT EXISTS `fadb` 
USE `fadb`;

--
-- Table structure for table `image`
--

DROP TABLE IF EXISTS `image`;
CREATE TABLE `image` (
  `image_id` int NOT NULL AUTO_INCREMENT,
  `project_fid` int NOT NULL,
  `image_path` varchar(260) NOT NULL,
  `image_name` varchar(260) NOT NULL,
  `image_ext` varchar(10) NOT NULL,
  `is_locked` bit(1) NOT NULL DEFAULT b'0',
  `is_labeled` bit(1) NOT NULL DEFAULT b'0',
  PRIMARY KEY (`image_id`),
  UNIQUE KEY `image_id_UNIQUE` (`image_id`),
  UNIQUE KEY `image_path_UNIQUE` (`image_path`),
  KEY `project_id_idx` (`project_fid`),
  CONSTRAINT `project_id` FOREIGN KEY (`project_fid`) REFERENCES `project` (`project_id`)
) ENGINE=InnoDB AUTO_INCREMENT=428 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `instance_seg_meta`
--

DROP TABLE IF EXISTS `instance_seg_meta`;
CREATE TABLE `instance_seg_meta` (
  `annotation_id` int NOT NULL AUTO_INCREMENT,
  `image_id` int NOT NULL,
  `mask_path` varchar(260) NOT NULL,
  `info_path` varchar(260) NOT NULL,
  `class_name` varchar(45) NOT NULL,
  PRIMARY KEY (`annotation_id`),
  UNIQUE KEY `mask_path_UNIQUE` (`mask_path`),
  UNIQUE KEY `info_path_UNIQUE` (`info_path`),
  UNIQUE KEY `annotation_id_UNIQUE` (`annotation_id`),
  KEY `image_fid_idx` (`image_id`),
  CONSTRAINT `image_fid` FOREIGN KEY (`image_id`) REFERENCES `image` (`image_id`)
) ENGINE=InnoDB AUTO_INCREMENT=137 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `project`
--

DROP TABLE IF EXISTS `project`;
CREATE TABLE `project` (
  `project_id` int NOT NULL AUTO_INCREMENT,
  `project_name` varchar(80) NOT NULL,
  `last_uploaded` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `unlabeled_count` int NOT NULL DEFAULT '0',
  `labeled_count` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`project_id`),
  UNIQUE KEY `project_id_UNIQUE` (`project_id`),
  UNIQUE KEY `project_name_UNIQUE` (`project_name`)
) ENGINE=InnoDB AUTO_INCREMENT=119 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;