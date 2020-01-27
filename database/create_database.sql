CREATE TABLE `project` (
  `project_id` int NOT NULL AUTO_INCREMENT,
  `project_name` varchar(80) NOT NULL,
  `last_uploaded` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `unlabeled_count` int NOT NULL DEFAULT '0',
  `labeled_count` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`project_id`),
  UNIQUE KEY `project_id_UNIQUE` (`project_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `` (`project_id`,`project_name`,`last_uploaded`,`unlabeled_count`,`labeled_count`) VALUES (1,'Test','2020-01-23 23:29:38',0,0);
INSERT INTO `` (`project_id`,`project_name`,`last_uploaded`,`unlabeled_count`,`labeled_count`) VALUES (2,'Test2','2020-01-23 23:31:12',0,0);
