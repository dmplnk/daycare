-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

drop schema kidgarten;
create schema if not exists `kidgarten`;
use `kidgarten`;

-- -----------------------------------------------------
-- Table `kidgarten`.`class`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `class` (
  `id` INT NOT NULL PRIMARY KEY ,
  `name` VARCHAR(45) NOT NULL);

-- -----------------------------------------------------
-- Table `kidgarten`.`group`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `group` (
  `id` INT NOT NULL PRIMARY KEY,
  `name` VARCHAR(45) NOT NULL,
  `tutor_id` INT NOT NULL)
  ;

-- -----------------------------------------------------
-- Table `kidgarten`.`kid`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `kid` (
  `id` INT NOT NULL PRIMARY KEY,
  `name` VARCHAR(30) NOT NULL,
  `surname` VARCHAR(45) NOT NULL,
  `patronymic` VARCHAR(45),
  `gender` VARCHAR(7) NOT NULL,
  `date_of_birth` DATE NOT NULL,
  `age` INT NOT NULL,
  `group_idgroup` INT NOT NULL);

-- -----------------------------------------------------
-- Table `kidgarten`.`parent`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `parent` (
  `id` INT NOT NULL PRIMARY KEY,
  `name` VARCHAR(30) NOT NULL,
  `surname` VARCHAR(45) NOT NULL,
  `patronymic` VARCHAR(45),
  `gender` VARCHAR(7) NOT NULL,
  `phone_number` VARCHAR(12) NOT NULL);

-- -----------------------------------------------------
-- Table `kidgarten`.`kid_has_parent`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `kid_has_parent` (
  `kid_id` INT NOT NULL,
  `parent_id` INT NOT NULL);

-- -----------------------------------------------------
-- Table `kidgarten`.`tutor`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `tutor` (
  `id` INT NOT NULL PRIMARY KEY,
  `name` VARCHAR(30) NOT NULL,
  `surname` VARCHAR(45) NOT NULL,
  `patronymic` VARCHAR(45) NULL DEFAULT NULL,
  `date_of_birth` DATE NOT NULL,
  `position` VARCHAR(45) NOT NULL,
  `phone_number` VARCHAR(12) NOT NULL,
  `chat_id` VARCHAR(45));

-- -----------------------------------------------------
-- Table `kidgarten`.`schedule`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `schedule` (
  `id` int not null PRIMARY KEY,
  `group_id` INT NOT NULL,
  `class_id` INT NOT NULL,
  `tutor_id` INT NOT NULL,
  `start_time` TIME NOT NULL,
  `end_time` TIME NOT NULL,
  `week_day` varchar(15) not null default "каждый день");

insert into kidgarten.group
values  (1, "Солнышки", 1),
		(2, "Звездочки", 4),
        (3, "Пчелки", 5);
        
insert into kidgarten.kid
values  (1, "Дарья", "Кузнецова", "Михайловна", "женский", "2019-08-15", 0, 2), -- 5 
		(2, "Мария", "Павлова", "Максимовна", "женский", "2020-03-27", 0, 1), -- 4 
        (3, "Александр", "Павлов", "Максимович", "мужской", "2018-05-12", 0, 3), -- 6 
        (4, "Лука", "Дементьев", "Дмитриевич", "мужской", "2019-10-04", 0, 2), -- 5 
        (5, "София", "Фадеева", "Алексеевна", "женский", "2018-07-06", 0, 3); -- 6 

update kid set age = (select age from (select id, YEAR(CURDATE()) - YEAR(date_of_birth) - (DATE_FORMAT(CURDATE(), '%m%d') < DATE_FORMAT(date_of_birth, '%m%d')) AS age 
from kid) as tablee where tablee.id = kid.id);  

insert into kidgarten.parent
values  (1, "Ксения", "Павлова", "Михайловна", "женский", "+79055457103"),
		(2, "Максим", "Павлов", "Романович", "мужской", "+79269264614"),
        (3, "Михаил", "Кузнецов", "Ильич", "мужской", "+79027658543"),
        (4, "Виктория", "Кузнецова", "Марковна", "женский", "+79253748797"),
        (5, "Есения", "Дементьева", "Николаевна", "женский", "+79067111903"),
        (6, "Ева", "Фадеева", "Евгеньевна", "женский", "+79223457658"),
        (7, "Алексей", "Фадеев", "Андреевич", "мужской", "+79035482365");
        
insert into kidgarten.kid_has_parent
values  (1, 3),
		(1, 4),
        (2, 1),
        (2, 2),
        (3, 1),
        (3, 2),
        (4, 5),
        (5, 6),
        (5, 7);
               
insert into kidgarten.tutor
values  (1, "Лариса", "Янышевская", "Валентиновна", "1989-06-12", "воспитатель", "+79259804244", '-1002331481998'),
		(2, "Наталия", "Галкина", "Дмитриевна", "1996-08-28", "музыкальный руководитель", "+79416778751", NULL),
        (3, "Ксения", "Абрамова", "Петровна", "1993-01-09", "логопед", "+79685966225", NULL),
        (4, "Раиса", "Федотова", "Юрьевна", "1981-05-22", "воспитатель", "+79481967859", '-4612506078'),
        (5, "Дарья", "Алимкина", "Давидовна", "1985-06-16", "воспитатель", "+79259804244", '-4700267237'),
        (6, "Лидия", "Мальцева", "Егоровна", "1988-08-10", "инструктор по физической культуре", "+79259804244", NULL),
        (7, "Ася", "Серых", "Артемова", "1992-12-03", "педагог-хореграф", "+79643367027", NULL);
        
insert into kidgarten.class
values  (1, "Приход детей"),
		(2, "Утренняя гимнастика"),
        (3, "Завтрак"),
        (4, "Танцы, театр"),
        (5, "Физическая культура"),
        (6, "Аппликация"),
        (7, "Знакомство с окружающим миром"),
        (8, "Рисование"),
        (9, "Музыка"),
        (10, "Лепка"),
        (11, "Развитие речи"),
        (12, "ФЭМП"),
        (13, "Овладение грамотой"),
        (14, "Свободное время, игра"),
        (15, "Прогулка"),
        (16, "Обед"),
        (17, "Сон"),
        (18, "Полдник");
        
insert into kidgarten.schedule
values  (1, 1, 1, 1, '8:30', '9:00', default),
		(2, 1, 2, 1, '9:00', '9:30', default),
        (3, 1, 3, 1, '9:30', '10:30', default),
        (4, 1, 4, 7, '10:30', '11:00', 'Пн'),
        (5, 1, 5, 6, '10:30', '11:00', 'Вт'),
        (6, 1, 6, 1, '10:30', '11:00', 'Ср'),
        (7, 1, 5, 6, '10:30', '11:00', 'Чт'),
        (8, 1, 7, 1, '10:30', '11:00', 'Пт'),
        (9, 1, 14, 1, '11:00', '11:30', default),
        (10, 1, 8, 1, '11:30', '12:00', 'Пн'),
        (11, 1, 7, 1, '11:30', '12:00', 'Вт'),
        (12, 1, 9, 2, '11:30', '12:00', 'Ср'),
        (13, 1, 8, 1, '11:30', '12:00', 'Чт'),
        (14, 1, 10, 1, '11:30', '12:00', 'Пт'),
		(15, 1, 14, 1, '12:00', '12:30', default),
        (16, 1, 15, 1, '12:30', '13:00', default),
        (17, 1, 16, 1, '13:00', '14:00', default),
        (18, 1, 17, 1, '14:00', '15:00', default),
        (19, 1, 14, 1, '15:00', '15:30', default),
        (20, 1, 18, 1, '15:30', '16:00', default),
        (21, 1, 11, 3, '16:30', '17:00', 'Пн'),
        (22, 1, 12, 1, '16:30', '17:00', 'Вт'),
        (23, 1, 11, 3, '16:30', '17:00', 'Ср'),
        (24, 1, 12, 1, '16:30', '17:00', 'Чт'),
        (25, 1, 11, 3, '16:30', '17:00', 'Пт'),
        (26, 1, 14, 1, '17:00', '17:30', default),
        (27, 1, 15, 1, '17:30', '18:00', default),
        (28, 2, 1, 4, '8:30', '9:00', default),
		(29, 2, 2, 4, '9:00', '9:30', default),
        (30, 2, 3, 4, '9:30', '10:30', default),
        (31, 2, 8, 4, '10:30', '11:30', 'Пн'),
        (32, 2, 6, 4, '10:30', '11:30', 'Вт'),
        (33, 2, 7, 4, '10:30', '11:30', 'Ср'),
        (34, 2, 10, 4, '10:30', '11:30', 'Чт'),
        (35, 2, 8, 4, '10:30', '11:30', 'Пт'),
        (36, 2, 14, 4, '11:30', '12:00', default),
        (37, 2, 7, 4, '12:00', '12:30', 'Пн'),
        (38, 2, 4, 7, '12:00', '12:30', 'Вт'),
        (39, 2, 5, 6, '12:00', '12:30', 'Ср'),
        (40, 2, 9, 2, '12:00', '12:30', 'Чт'),
        (41, 2, 5, 6, '12:00', '12:30', 'Пт'),
        (42, 2, 15, 4, '12:30', '13:00', default),
        (43, 2, 16, 4, '13:00', '14:00', default),
        (44, 2, 17, 4, '14:00', '15:00', default),
        (45, 2, 14, 4, '15:00', '15:30', default),
        (46, 2, 18, 4, '15:30', '16:00', default),
        (47, 2, 11, 3, '16:30', '17:00', 'Пн'),
        (48, 2, 12, 1, '16:30', '17:00', 'Вт'),
        (49, 2, 13, 3, '16:30', '17:00', 'Ср'),
        (50, 2, 12, 4, '16:30', '17:00', 'Чт'),
        (51, 2, 13, 3, '16:30', '17:00', 'Пт'),
        (52, 2, 14, 4, '17:00', '17:30', default),
        (53, 2, 15, 4, '17:30', '18:00', default),
		(54, 3, 1, 5, '8:30', '9:00', default),
		(55, 3, 2, 5, '9:00', '9:30', default),
        (56, 3, 3, 5, '9:30', '10:30', default),
        (57, 3, 13, 3, '10:30', '11:30', 'Пн'),
        (58, 3, 12, 5, '10:30', '11:30', 'Вт'),
        (59,3, 13, 3, '10:30', '11:30', 'Ср'),
        (60, 3, 12, 5, '10:30', '11:30', 'Чт'),
        (61, 3, 7, 5, '10:30', '11:30', 'Пт'),
        (62, 3, 14, 5, '11:30', '12:00', default),
        (63, 3, 4, 7, '12:00', '12:30', 'Пн'),
        (64, 3, 5, 6, '12:00', '12:30', 'Вт'),
        (65, 3, 9, 2, '12:00', '12:30', 'Ср'),
        (66, 3, 5, 6, '12:00', '12:30', 'Чт'),
        (67, 3, 12, 5, '12:00', '12:30', 'Пт'),
        (68, 3, 15, 5, '12:30', '13:00', default),
        (69, 3, 16, 5, '13:00', '14:00', default),
        (70, 3, 17, 5, '14:00', '15:00', default),
        (71, 3, 14, 5, '15:00', '15:30', default),
        (72, 3, 18, 5, '15:30', '16:00', default),
        (73, 3, 8, 5, '16:30', '17:00', 'Пн'),
        (74, 3, 7, 5, '16:30', '17:00', 'Вт'),
        (75, 3, 10, 5, '16:30', '17:00', 'Ср'),
        (76, 3, 8, 5, '16:30', '17:00', 'Чт'),
        (77, 3, 6, 5, '16:30', '17:00', 'Пт'),
        (78, 3, 14, 5, '17:00', '17:30', default),
        (79, 3, 15, 5, '17:30', '18:00', default);
        
(select start_time, end_time, class.name as 'class name', tutor.name, surname from kidgarten.schedule
join kidgarten.tutor on kidgarten.schedule.tutor_id = kidgarten.tutor.id
join kidgarten.class on kidgarten.schedule.class_id= kidgarten.class.id
where group_id = 2 and (week_day = 'каждый день' or week_day = 'Вт')
order by start_time);


update kid set age = (select age from (select id, YEAR(CURDATE()) - YEAR(date_of_birth) - (DATE_FORMAT(CURDATE(), '%m%d') < DATE_FORMAT(date_of_birth, '%m%d')) AS age 
from kid) as tablee where tablee.id = kid.id);  
select name from kid inner join (select kid_id from kid_has_parent where parent_id = 3) as tablee on tablee.kid_id =kid.id;

select kid.name, surname, patronymic, gender, date_of_birth, age, `group`.name from kid 
inner join `group` on kid.group_idgroup = `group`.id
where kid.id = 2;
