START TRANSACTION;

DROP DATABASE IF EXISTS ogre;
CREATE DATABASE ogre;
USE ogre;

CREATE TABLE user (
	id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, 
	username VARCHAR(80) NOT NULL, 
	password VARCHAR(256) NOT NULL,
	email VARCHAR(120) NOT NULL,
	display_name VARCHAR(50) NULL,
	api_key_expires VARCHAR(23) NULL,
	points INTEGER NOT NULL DEFAULT 0,
	needs_password_reset BOOLEAN NOT NULL DEFAULT 1
);

CREATE TABLE user_badge (
	id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, 
	user_id INTEGER NOT NULL,
	badge INTEGER NOT NULL,
   	been_alerted BOOLEAN NOT NULL DEFAULT 0,
	UNIQUE KEY idx (user_id, badge)
);

CREATE TABLE log (
	id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, 
	user_id INTEGER NOT NULL,
	api_session_key VARCHAR(256), 
	timestamp DATE,
	type VARCHAR(30),
   	data VARCHAR(200)
);


CREATE TABLE ogre_books (
	id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, 
	authortitle VARCHAR(500),
	users VARCHAR(200),
	formats VARCHAR(200),
	tags VARCHAR(200),
	sdbkey VARCHAR(256),
	UNIQUE KEY idx (sdbkey)
);

CREATE TABLE ogre_formats (
	id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, 
	authortitle VARCHAR(500),
	format VARCHAR(20),
	version_count INTEGER,
	sdbkey VARCHAR(256),
	UNIQUE KEY idx (authortitle, format)
);

CREATE TABLE ogre_versions (
	id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, 
	authortitle VARCHAR(500),
	version INTEGER,
	format VARCHAR(20),
	user VARCHAR(200),
	size INTEGER,
	filehash VARCHAR(256),
   	uploaded BOOLEAN,
   	dedrm BOOLEAN,
	sdbkey VARCHAR(256),
	UNIQUE KEY idx (authortitle, version, format)
);

CREATE TABLE ogre_book_comments (
	id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, 
	authortitle VARCHAR(500),
	sdbkey VARCHAR(256),
	username VARCHAR(50),
	comment VARCHAR(4000),
	UNIQUE KEY idx (sdbkey, username)
);

CREATE TABLE ogre_book_ratings (
	id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, 
	authortitle VARCHAR(500),
	sdbkey VARCHAR(256),
	username VARCHAR(50),
	rating INTEGER,
	UNIQUE KEY idx (sdbkey, username)
);

CREATE TABLE ogre_book_tags (
	id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT, 
	authortitle VARCHAR(500),
	sdbkey VARCHAR(256),
	tag VARCHAR(50),
	UNIQUE KEY idx (sdbkey)
);

COMMIT;
