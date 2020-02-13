CREATE SCHEMA `fadb` DEFAULT CHARACTER SET utf8 ;

CREATE TABLE `fadb`.`project` (
  `project_id` int NOT NULL AUTO_INCREMENT,
  `project_name` varchar(80) NOT NULL,
  `last_uploaded` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `unlabeled_count` int NOT NULL DEFAULT '0',
  `labeled_count` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`project_id`),
  UNIQUE KEY `project_id_UNIQUE` (`project_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `image` (
  `image_id` int NOT NULL AUTO_INCREMENT,
  `file_path` varchar(260) NOT NULL,
  `project_fid` int NOT NULL,
  PRIMARY KEY (`image_id`),
  UNIQUE KEY `image_id_UNIQUE` (`image_id`),
  UNIQUE KEY `file_path_UNIQUE` (`file_path`),
  KEY `project_id_idx` (`project_fid`),
  CONSTRAINT `project_id` FOREIGN KEY (`project_fid`) REFERENCES `project` (`project_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;