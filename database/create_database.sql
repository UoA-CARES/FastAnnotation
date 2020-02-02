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