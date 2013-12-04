CREATE TABLE url (site VARCHAR(20), id INTEGER, subject VARCHAR(1024), primary key(site, id));
CREATE TABLE article (site VARCHAR(20), url_id INTEGER, id INTEGER, subject VARCHAR(1024), link VARCHAR(1024), primary key (site, url_id, id));
