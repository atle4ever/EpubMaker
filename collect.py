import urllib2
import sqlite3 as lite
from lxml import etree

url_id = 14104
url = 'http://novel.munpia.com/14104' # write the url here

# init sqlite3
con = lite.connect('feed.db')
cur = con.cursor()

# get url_id and subject
cur.execute("SELECT id, subject FROM url")
urls = cur.fetchall()

for url in urls:
    url_id = url[0]
    url = "http://novel.munpia.com/{0}".format(url_id)
    url_subject = url[1]

    # get html
    usock = urllib2.urlopen(url)
    doc = usock.read()
    usock.close()
    
    # html parsing
    hparser = etree.HTMLParser(encoding='utf-8')
    doc = etree.fromstring(doc, hparser)
    articles = doc.xpath("//*[@id=\"ENTRIES\"]/tbody/tr")
    for a in articles:
        article_id = a.xpath("./td[1]/span/text()")[0]
        article_subject = a.xpath("./td[2]/a[1]/text()")[0]
        article_link = 'http://novel.munpia.com' + a.xpath("./td[2]/a[1]/@href")[0]
        article_date = a.xpath("./td[3]/text()")[0]
    
        cur.execute("SELECT count(*) FROM article WHERE url_id = ? AND id = ?", (url_id, article_id))
        ret = cur.fetchall()

        # new article
        if(ret[0][0] == 0): 
            cur.execute("INSERT INTO article VALUES (?, ?, ?, ?)",
                    (url_id, article_id, article_subject, article_link))
            print "New article {0} {1} {2}".format(url_id, article_id, article_link)
    
    con.commit()

con.close()
