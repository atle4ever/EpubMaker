CREATE TABLE url (id INTEGER primary key, subject VARCHAR(1024));
CREATE TABLE article (url_id INTEGER, id INTEGER, subject VARCHAR(1024), link VARCHAR(1024), primary key (url_id, id));
