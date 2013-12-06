import urllib2
import sqlite3 as lite
import sys
from lxml import etree
from webhelpers.feedgenerator import Atom1Feed
import logging

# create logger with 'spam_application'
logger = logging.getLogger('FeedMaker')
logger.setLevel(logging.DEBUG)

# create file handler which logs even debug messages
fh = logging.FileHandler('log')

# create console handler with a higher log level
ch = logging.StreamHandler()

# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)



RUN_DIR = '/home/sjkim/FeedMaker/'
DROPBOX_PUBIC = '/home/sjkim/Dropbox/public/'

class SqliteConnect:
    def __init__(self, dbPath):
        # TODO: check whether db exist
        self.con = lite.connect(dbPath)
        self.cur = self.con.cursor()

    xpath = {
            'munpia': {
                'UrlFormat': "http://novel.munpia.com/{0}",
                'FeedSubject': "//*[@id=\"board\"]/div[1]/div[2]/h2/a/text()",
                'Articles': "//*[@id=\"ENTRIES\"]/tbody/tr",
                'ArticleLink': ["./td[2]/a[1]/@href", ],
                'ArticleSubject': ["./td[2]/a[1]/text()", ],
                'ArticleId': "./td[1]/span/text()",
                'ArticleDate': "./td[3]/text()",
                'ArticleLinkPrefix': 'http://novel.munpia.com',
                },
            'naver': {
                'UrlFormat': "http://novel.naver.com/webnovel/list.nhn?novelId={0}",
                'FeedSubject': "//*[@id=\"content\"]/div/div[1]/div[1]/div/h2/text()",
                'Articles': "//*[@id=\"content\"]/div/div[1]/table/tbody/tr",
                'ArticleLink': ["./td[1]/a/@href", "./td[1]/div/a/@href"],
                'ArticleSubject': ["./td[1]/a/text()", "./td[1]/div/a/text()"],
                'ArticleId': '', 
                'ArticleDate': "./td[2]/text()",
                'ArticleLinkPrefix': 'http://novel.naver.com/',
                },
            }

    def getXPath(self, site, target):
        siteXPath = self.xpath.get(site)
        assert siteXPath != None, "Invalid site: '{0}'".format(site)

        xp = siteXPath.get(target);
        assert xp != None, "Invalid target: '{0}' for '{1}'".format(target, site)

        return xp
            
    def genUrl(self, site, url_id):
        return self.getXPath(site, 'UrlFormat').format(url_id)

    def commit(self):
        self.con.commit()

class Crawler(SqliteConnect):
    def publish(self, site, url_id, url_subject):
        url = self.genUrl(site, url_id)
    
        feed = Atom1Feed(
                title=url_subject,
                link=url,
                description=url_subject,
                language=u"kr",
                )
    
        self.cur.execute("SELECT subject, link FROM article WHERE site = ? AND url_id = ? order by id desc", (site, url_id))
        ret = self.cur.fetchall()
        for a in ret:
            article_subject = a[0]
            article_link = a[1]
            feed.add_item(title=article_subject,
                    link=article_link,
                    description="")
    
        xml = open(DROPBOX_PUBIC + "{0}_{1}.xml".format(site, url_id), "w")
        xml.write(feed.writeString('utf-8'))
        xml.close()

        logger.info(u"feed is generated: {0}, {1}{2}_{3}.xml".format(url_subject, DROPBOX_PUBIC, site, url_id))
    
    def crawl(self):
        # get url_id and subject
        self.cur.execute("SELECT site, id, subject FROM url")
        urls = self.cur.fetchall()
        
        for url in urls:
            site = url[0]
            url_id = url[1]
            url_subject = url[2]
            
            # get html
            url = self.genUrl(site, url_id)
            usock = urllib2.urlopen(url)
            doc = usock.read()
            usock.close()

            hasNew = self.crawlFeed(site, url_id, doc)

            if hasNew == True:
                self.con.commit()
                self.publish(site, url_id, url_subject)
        self.con.close()

    def crawlFeed(self, site, url_id, doc):
        # html parsing
        hparser = etree.HTMLParser(encoding='utf-8')
        doc = etree.fromstring(doc, hparser)
        articles = doc.xpath(self.getXPath(site, 'Articles'))
        hasNew = False
        for a in articles:
            article_class = a.xpath("./@class")
            if len(article_class) > 0 and article_class[0] == "notice":
                continue

            for xp in self.getXPath(site, 'ArticleLink'):
                link_node = a.xpath(xp)
                if len(link_node) != 0: break;
            assert len(link_node) != 0, "Fail to get article's link"
            article_link = self.getXPath(site, 'ArticleLinkPrefix') + link_node[0]

            for xp in self.getXPath(site, 'ArticleSubject'):
                subject_node = a.xpath(xp)
                if len(subject_node) != 0: break;
            assert len(subject_node) != 0, "Fail to get article's subject"
            article_subject = subject_node[0]
    
            xp = self.getXPath(site, 'ArticleId')
            if xp == '':
                assert site == 'naver'
                article_id = article_link[article_link.rfind('volumeNo=') + 9:];
            else:
                article_id = a.xpath(xp)[0]
            article_date = a.xpath("./td[2]/text()")[0]
    
            self.cur.execute("SELECT count(*) FROM article WHERE site = ? AND url_id = ? AND id = ?", (site, url_id, article_id))
            ret = self.cur.fetchall()
    
            # new article
            if(ret[0][0] == 0): 
                self.cur.execute("INSERT INTO article(site, url_id, id, subject, link) VALUES (?, ?, ?, ?, ?)",
                        (site, url_id, article_id, article_subject, article_link))
                logger.info( u"New article is added: {0} ({1}, {2})".format(article_subject, article_id, article_link) )
                hasNew = True
    
        return hasNew

class FeedManager(SqliteConnect):
    def addFeed(self, site, url_id):
        # get url_id and subject
        self.cur.execute("SELECT count(*) FROM url WHERE site = ? AND id = ?", (site, url_id))
        ret = self.cur.fetchone()
        if ret[0] != 0:
            logger.warning ( u"Existing url id {0}".format(url_id) )
            return False
    
        # get subject
        url = self.genUrl(site, url_id)
        usock = urllib2.urlopen(url)
        doc = usock.read()
        usock.close()
            
        hparser = etree.HTMLParser(encoding='utf-8')
        doc = etree.fromstring(doc, hparser)
        subject = doc.xpath(self.getXPath(site, 'FeedSubject'))[0].strip()
    
        self.cur.execute("INSERT INTO url(site, id, subject) VALUES (?, ?, ?)", (site, url_id, subject))
        logger.info( u"New feed is added: {0} ({1}, {2})".format(subject, site, url_id) )
        self.con.commit()

        return True

def main():
    def usage():
        logger.error( "Invalid usage" )
        logger.error( "usage 1: python {0} crawl".format(sys.argv[0]) )
        logger.error( "usage 2: python {0} add <site> <url id>".format(sys.argv[0]) )
        return
    
    # init Crawer, FeedManager
    crawler = Crawler('/home/sjkim/FeedMaker/feed.db')
    manager = FeedManager('/home/sjkim/FeedMaker/feed.db')
    
    if len(sys.argv) == 1:
        usage()
        sys.exit(-1)
    
    if sys.argv[1] == 'crawl':
        crawler.crawl()
    else: # add command
        if len(sys.argv) < 4:
            usage()
            sys.exit(-1)
    
        site = sys.argv[2]
        url_id = int(sys.argv[3])
    
        manager.addFeed(site, url_id)

if __name__ == "__main__":
    main()
