CREATE TABLE `deployment` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `label` varchar(100) NOT NULL,
  `type` enum('pr','branch') NOT NULL DEFAULT 'pr',
  `source_branch` varchar(100) NOT NULL,
  `source_sha` varchar(40) NOT NULL,
  `deployed_at` timestamp NULL DEFAULT NULL,
  `title` varchar(255) DEFAULT NULL,
  `url` varchar(255) DEFAULT NULL,
  `author` varchar(100) DEFAULT NULL,
  `fail_count` int(10) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `label_UK` (`label`)
) DEFAULT CHARSET=utf8mb4;