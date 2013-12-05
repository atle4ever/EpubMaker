import urllib2
import sqlite3 as lite
import sys
from lxml import etree
from webhelpers.feedgenerator import Atom1Feed

RUN_DIR = '/home/sjkim/FeedMaker/'
DROPBOX_PUBIC = '/home/sjkim/Dropbox/public/'

def publish(cur, site, url_id, url_subject):
    if site == 'munpia':
        url = "http://novel.munpia.com/{0}".format(url_id)
    elif site == 'naver':
        url = "http://novel.naver.com/webnovel/list.nhn?novelId={0}".format(url_id)
    else:
        print "Error: invliad site {0}".format(site)
        sys.exit(-1)

    feed = Atom1Feed(
            title=url_subject,
            link=url,
            description=url_subject,
            language=u"kr",
            )


    cur.execute("SELECT subject, link FROM article WHERE site = ? AND url_id = ? order by id desc", (site, url_id))
    ret = cur.fetchall()
    for a in ret:
        article_subject = a[0]
        article_link = a[1]
        feed.add_item(title=article_subject,
                link=article_link,
                description="")

    xml = open(DROPBOX_PUBIC + "{0}_{1}.xml".format(site, url_id), "w")
    xml.write(feed.writeString('utf-8'))
    xml.close()

def crawl():
    # init sqlite3
    con = lite.connect(RUN_DIR + 'feed.db')
    cur = con.cursor()
    
    # get url_id and subject
    cur.execute("SELECT site, id, subject FROM url")
    urls = cur.fetchall()
    
    for url in urls:
        site = url[0]
        url_id = url[1]
        url_subject = url[2]
        
        if site == 'munpia':
            url = "http://novel.munpia.com/{0}".format(url_id)
            hasNew = crawlMunpia(cur, url, url_id, url_subject)

        elif site == 'naver':
            url = "http://novel.naver.com/webnovel/list.nhn?novelId={0}".format(url_id)
            hasNew = crawlNaver(cur, url, url_id, url_subject);

        else:
            print "Error: invliad site {0}".format(site)
            sys.exit(-1)
        con.commit()

        if hasNew == True:
            publish(cur, site, url_id, url_subject)

    con.close()
    
def crawlNaver(cur, url, url_id, url_subject):
    # get html
    usock = urllib2.urlopen(url)
    doc = usock.read()
    usock.close()

    # html parsing
    hparser = etree.HTMLParser(encoding='utf-8')
    doc = etree.fromstring(doc, hparser)
    articles = doc.xpath("//*[@id=\"content\"]/div/div[1]/table/tbody/tr")
    hasNew = False
    for a in articles:
        link_node = a.xpath("./td[1]/a/@href")
        if len(link_node) == 0: link_node = a.xpath("./td[1]/div/a/@href")
        article_link = 'http://novel.naver.com/' + link_node[0]

        subject_node = a.xpath("./td[1]/a/text()")
        if len(subject_node) == 0: subject_node = a.xpath("./td[1]/div/a/text()")
        article_subject = subject_node[0]

        article_id = article_link[article_link.rfind('volumeNo=') + 9:];
        article_date = a.xpath("./td[2]/text()")[0]

        cur.execute("SELECT count(*) FROM article WHERE site = ? AND url_id = ? AND id = ?", ('naver', url_id, article_id))
        ret = cur.fetchall()

        # new article
        if(ret[0][0] == 0): 
            cur.execute("INSERT INTO article(site, url_id, id, subject, link) VALUES (?, ?, ?, ?, ?)",
                    ('naver', url_id, article_id, article_subject, article_link))
            print "New article {0} {1} {2}".format(url_id, article_id, article_link)
            hasNew = True

    return hasNew

def crawlMunpia(cur, url, url_id, url_subject):
    # get html
    usock = urllib2.urlopen(url)
    doc = usock.read()
    usock.close()
    
    # html parsing
    hparser = etree.HTMLParser(encoding='utf-8')
    doc = etree.fromstring(doc, hparser)
    articles = doc.xpath("//*[@id=\"ENTRIES\"]/tbody/tr")
    hasNew = False
    for a in articles:
        article_class = a.xpath("./@class")
        if len(article_class) > 0 and article_class[0] == "notice":
            continue
        article_id = a.xpath("./td[1]/span/text()")[0]
        article_subject = a.xpath("./td[2]/a[1]/text()")[0]
        article_link = 'http://novel.munpia.com' + a.xpath("./td[2]/a[1]/@href")[0]
        article_date = a.xpath("./td[3]/text()")[0]
    
        cur.execute("SELECT count(*) FROM article WHERE site = ? AND url_id = ? AND id = ?", ('munpia', url_id, article_id))
        ret = cur.fetchall()

        # new article
        if(ret[0][0] == 0): 
            cur.execute("INSERT INTO article(site, url_id, id, subject, link) VALUES (?, ?, ?, ?, ?)",
                    ('munpia', url_id, article_id, article_subject, article_link))
            print "New article {0} {1} {2}".format(url_id, article_id, article_link)
            hasNew = True
    
    return hasNew

def newUrlNaver(site, url_id):
    # init sqlite3
    con = lite.connect(RUN_DIR + 'feed.db')
    cur = con.cursor()
    
    # get url_id and subject
    cur.execute("SELECT count(*) FROM url WHERE site = ? AND id = ?", (site, url_id))
    ret = cur.fetchone()
    if ret[0] != 0:
        print "Existing url id"
        return

    # get subject
    url = "http://novel.naver.com/webnovel/list.nhn?novelId={0}".format(url_id)
    usock = urllib2.urlopen(url)
    doc = usock.read()
    usock.close()
        
    hparser = etree.HTMLParser(encoding='utf-8')
    doc = etree.fromstring(doc, hparser)
    subject = doc.xpath("//*[@id=\"content\"]/div/div[1]/div[1]/div/h2/text()")[0].strip()

    cur.execute("INSERT INTO url(site, id, subject) VALUES (?, ?, ?)", (site, url_id, subject))
    print "New url id: {0}".format(url_id)
    con.commit()
    con.close()

def newUrlMunpia(site, url_id):
    # init sqlite3
    con = lite.connect(RUN_DIR + 'feed.db')
    cur = con.cursor()
    
    # get url_id and subject
    cur.execute("SELECT count(*) FROM url WHERE site = ? AND id = ?", (site, url_id))
    ret = cur.fetchone()
    if ret[0] != 0:
        print "Existing url id"
        return

    # get subject
    url = "http://novel.munpia.com/{0}".format(url_id)
    usock = urllib2.urlopen(url)
    doc = usock.read()
    usock.close()
        
    hparser = etree.HTMLParser(encoding='utf-8')
    doc = etree.fromstring(doc, hparser)
    subject = doc.xpath("//*[@id=\"board\"]/div[1]/div[2]/h2/a/text()")[0]

    cur.execute("INSERT INTO url(site, id, subject) VALUES (?, ?, ?)", (site, url_id, subject))
    print "New url id: {0}".format(url_id)
    con.commit()
    con.close()

def usage():
    print "usage 1: python {0} crawl".format(sys.argv[0])
    print "usage 2: python {0} add <site> <url id>".format(sys.argv[0])
    return

if len(sys.argv) == 1:
    usage()
    sys.exit(-1)

if sys.argv[1] == 'crawl':
    crawl()
else: # add command
    if len(sys.argv) < 4:
        usage()
        sys.exit(-1)

    site = sys.argv[2]
    url_id = int(sys.argv[3])

    if site == 'munpia':
        newUrlMunpia(site, url_id)
    elif site == 'naver':
        newUrlNaver(site, url_id)
    else:
        print "Invalid site {0}".format(site)
        sys.exit(-1)
