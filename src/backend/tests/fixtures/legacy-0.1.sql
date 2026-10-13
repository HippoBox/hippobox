BEGIN TRANSACTION;
CREATE TABLE api_key (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	access_key VARCHAR NOT NULL, 
	secret_hash VARCHAR NOT NULL, 
	total_requests INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	last_used_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);
CREATE TABLE auth (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	provider VARCHAR NOT NULL, 
	identifier VARCHAR NOT NULL, 
	last_login_at DATETIME, 
	last_login_ip VARCHAR, 
	last_login_user_agent VARCHAR, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);
INSERT INTO "auth" VALUES(1,1,'email','legacy@example.com',NULL,NULL,NULL,'2026-10-13 12:47:05.530485','2026-10-13 12:47:05.530487');
CREATE TABLE credential (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	password_hash VARCHAR NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	password_changed_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);
INSERT INTO "credential" VALUES(1,1,'$argon2id$v=19$m=65536,t=3,p=4$GCMkxNi7d845p7RWCmGMsQ$iCmN1WtmbnmeePV1agQNxccOBRFHeXUUyT5fEVezxxc',1,'2026-10-13 12:47:05.527458','2026-10-13 12:47:05.528084','2026-10-13 12:47:05.528086');
CREATE TABLE knowledge (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	topic_id INTEGER NOT NULL, 
	title VARCHAR NOT NULL, 
	content TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_knowledge_user_title UNIQUE (user_id, title), 
	FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE, 
	FOREIGN KEY(topic_id) REFERENCES topic (id) ON DELETE RESTRICT
);
INSERT INTO "knowledge" VALUES(1,1,1,'Before platform','Existing content','2026-10-13 12:47:05.533100','2026-10-13 12:47:05.533100');
CREATE TABLE knowledge_tag (
	knowledge_id INTEGER NOT NULL, 
	tag_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (knowledge_id, tag_id), 
	FOREIGN KEY(knowledge_id) REFERENCES knowledge (id) ON DELETE CASCADE, 
	FOREIGN KEY(tag_id) REFERENCES tag (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);
INSERT INTO "knowledge_tag" VALUES(1,1,1,'2026-10-13 12:47:05.534875');
CREATE TABLE tag (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	normalized_name VARCHAR NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_tag_user_norm UNIQUE (user_id, normalized_name), 
	FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);
INSERT INTO "tag" VALUES(1,1,'retained','retained','2026-10-13 12:47:05.534493');
CREATE TABLE topic (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	normalized_name VARCHAR NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_topic_user_norm UNIQUE (user_id, normalized_name), 
	FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);
INSERT INTO "topic" VALUES(1,1,'Legacy','legacy','2026-10-13 12:47:05.532796');
CREATE TABLE user (
	id INTEGER NOT NULL, 
	email VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	role VARCHAR(5) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	is_verified BOOLEAN NOT NULL, 
	guide_seen BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email), 
	UNIQUE (name)
);
INSERT INTO "user" VALUES(1,'legacy@example.com','legacy','USER',1,1,0,'2026-10-13 12:47:05.492736','2026-10-13 12:47:05.492740');
CREATE INDEX ix_auth_identifier ON auth (identifier);
CREATE UNIQUE INDEX ix_auth_user_id ON auth (user_id);
CREATE UNIQUE INDEX ix_credential_user_id ON credential (user_id);
CREATE INDEX ix_api_key_access_key ON api_key (access_key);
CREATE UNIQUE INDEX ix_api_key_secret_hash ON api_key (secret_hash);
CREATE INDEX ix_api_key_user_id ON api_key (user_id);
CREATE INDEX ix_topic_user_id ON topic (user_id);
CREATE INDEX ix_topic_normalized_name ON topic (normalized_name);
CREATE INDEX ix_tag_normalized_name ON tag (normalized_name);
CREATE INDEX ix_tag_user_id ON tag (user_id);
CREATE INDEX ix_knowledge_user_id ON knowledge (user_id);
CREATE INDEX ix_knowledge_topic_id ON knowledge (topic_id);
CREATE INDEX ix_knowledge_tag_user_id ON knowledge_tag (user_id);
COMMIT;
