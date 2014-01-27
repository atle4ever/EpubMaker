#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib2
import sqlite3 as lite
import sys
from lxml import etree
import logging
import ConfigParser
import codecs

from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders

import os, sys, subprocess
from config import *

# logger settting
logger = logging.getLogger('EpubMaker')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')

fh = logging.FileHandler('log')
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

# Send mail via gmail (ref from https://github.com/ChristophGr/rss4kindle)
def attachFilesToMessages(msg, files):
    for f in files:
        part = MIMEBase('application', "octet-stream")
        content = open(f,"rb").read()
        part.set_payload(content)
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"'
                       % os.path.basename(f))
        msg.attach(part)

def attachBodyToMessages(msg, content):
    body = ""
    for c in content:
        body += u'<a href="{0}">{1}</a><br />'.format(c[3], c[0])

    msg.attach(MIMEText(body, 'html', 'utf-8'))

def createMessage(to, subject):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_ACCOUNT
    msg['To'] = COMMASPACE.join(to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    return msg

def sendMailWithFiles(subject, emails, content, files):
    import smtplib
    server = smtplib.SMTP( "smtp.gmail.com", 587 )
    server.starttls()
    server.login(GMAIL_ACCOUNT, GMAIL_PASSWORD)
    subject = u"[EpubMaker] {0}: ({1}){2}".format(subject, content[0][2], content[0][0])

    msg = createMessage(emails.split(' '), subject)
    attachBodyToMessages(msg, content)
    attachFilesToMessages(msg, files)
    logger.debug("sending %s " % files)
    server.sendmail(GMAIL_ACCOUNT, emails.split(' '), msg.as_string())
    server.close()

class SqliteConnect:
    def __init__(self, dbPath):
        # TODO: check whether db exist
        self.con = lite.connect(dbPath)
        self.cur = self.con.cursor()

        existing = self.cur.execute("SELECT name FROM sqlite_master WHERE type = 'table' and name = 'url'").fetchone()
        if existing:
            return
        self.cur.execute("CREATE TABLE url (site VARCHAR(20), id INTEGER, subject VARCHAR(1024), minArticleId INTEGER, emails VARCHAR(1024), primary key(site, id))")

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
                'Content': "//*[@class=\"tcontent\"]",
                'PagePrefix': "/page/",
                'WriterMsg': '//*[@id="ENTRY-CONTENT"]/dl',
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
                'Content': "//*[@id=\"content\"]/div[1]/div[3]/div[1]",
                'PagePrefix': "&page=",
                'WriterMsg': '//*[@id="content"]/div[1]/div[4]/dl',
                },

            'naver_challenge': {
                'UrlFormat': "http://novel.naver.com/challenge/list.nhn?novelId={0}",
                'FeedSubject': "//*[@id=\"content\"]/div/div[1]/div[1]/div/h2/text()",
                'Articles': "//*[@id=\"content\"]/div/div[1]/table/tbody/tr",
                'ArticleLink': ["./td[1]/a/@href", "./td[1]/div/a/@href"],
                'ArticleSubject': ["./td[1]/a/text()", "./td[1]/div/a/text()"],
                'ArticleId': '', 
                'ArticleDate': "./td[2]/text()",
                'ArticleLinkPrefix': 'http://novel.naver.com/',
                'Content': "//*[@id=\"content\"]/div[1]/div[3]/div[1]",
                'PagePrefix': "&page=",
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

    def getContent(self, site, link):
        # get html
        usock = urllib2.urlopen(link)
        doc = usock.read()
        usock.close()

        # convert windows newline into unix style (for naver)
        if site[0:5] == 'naver':
            doc = doc.replace('\r\n', '<br />')

        # html parsing
        hparser = etree.HTMLParser(encoding='utf-8')
        doc = etree.fromstring(doc, hparser)
        contents = doc.xpath(self.getXPath(site, 'Content'))
        assert len(contents) == 1
        content = contents[0]
    
        # for naver, remove icons from content
        if site[0:5] == 'naver':
            talks = content.xpath("./p[@class=\"talk\"]")
            for t in talks:
                child = t.xpath("./a[@class=\"ico_talk _toggleDialogLayer()\"]")
                
                if len(child) == 1:
                    t.remove(child[0])
                elif len(child) == 0:
                    continue
                else:
                    assert False

            icons = content.xpath("./p/span[@class=\"ly_iconoff_wrap\"]")
            for ic in icons:
                child = ic.xpath("./span")
                assert len(child) == 1
                ic.remove(child[0])

        # get writer's comments
        comments = doc.xpath(self.getXPath(site, 'WriterMsg'))
        if len(comments) == 1:
            content.append(comments[0])
        
        content = etree.tostring(content)

        # add link to content and comments
        content += u'<a href="{0}">[본문 링크]</a>'.format(link)
        if site == 'munpia':
            content += u'<a href="{0}/nvView/viewComments/">[댓글 보기]</a>'.format(link)
        content += '<br />'

        return content


class Crawler(SqliteConnect):
    def crawl(self):
        # get url_id and subject
        self.cur.execute("SELECT site, id, subject, minArticleId, emails FROM url")
        urls = self.cur.fetchall()
        
        # run Xvfb for ebook-convert
        x = None
        env = os.environ
        if "DISPLAY" not in env:
            logger.info("starting temporary Xserver")
            x = subprocess.Popen("exec Xvfb :2 -screen 0 800x600x24", shell=True)
            env["DISPLAY"] = "localhost:2"

        for url in urls:
            site = url[0]
            url_id = url[1]
            url_subject = url[2]
            minArticleId = url[3]
            emails = url[4]
            
            self.crawlFeed(site, url_id, url_subject, minArticleId, emails, env)
            self.con.commit()

        self.con.close()

        if x != None:
            logger.info("terminating temporary Xserver")
            x.terminate()

    def genUrlWithPage(self, site, url_id):
        return self.genUrl(site, url_id) + self.getXPath(site, 'PagePrefix')
        
    def crawlFeed(self, site, url_id, url_subject, minArticleId, emails, env):
        logger.info(u"Start feed {0} ({1}, {2})".format(url_subject, site, url_id))

        pageId = 1
        urlPrefix = self.genUrlWithPage(site, url_id)

        updateMinArticleId = True
        contents = []
        while True:
            # set url of article list
            urlArticleList = urlPrefix + str(pageId)

            # get html
            usock = urllib2.urlopen(urlArticleList)
            doc = usock.read()
            usock.close()

            endLoop = self.crawlList(site, url_id, doc, contents, minArticleId, updateMinArticleId)

            # check whether this page is last
            if endLoop:
                break

            pageId += 1
            updateMinArticleId = False
            
        if len(contents) == 0:
            return
        

        contents.reverse()

        # generate html ebook
        htmlFile = "{0}_{1}.html".format(site, url_id)
        htmlFile = os.path.join(FILESTORAGE, htmlFile)
        epubFile = "{0}_{1}.epub".format(site, url_id)
        epubFile = os.path.join(FILESTORAGE, epubFile)
        html = codecs.open(htmlFile, 'w', encoding='utf-8')
        html.write(u"<html><head><title>{0}</title></head><body>".format(url_subject))
        for c in contents:
            html.write(u"<h2 class=\"chapter\">{0}</h2>".format(c[0]))
            html.write(c[1])
        html.write(u"</body></html>")
        html.close()

        # convert html to epub
        subprocess.call( ["ebook-convert", htmlFile, epubFile, "--no-default-epub-cover"] , env = env)

        sendMailWithFiles(url_subject, emails, contents, [epubFile])

    def crawlList(self, site, url_id, doc, contents, minArticleId, updateMinArticleId):
        # html parsing
        hparser = etree.HTMLParser(encoding='utf-8')
        doc = etree.fromstring(doc, hparser)
        articles = doc.xpath(self.getXPath(site, 'Articles'))

        for a in articles:
            # check whether article is notice. If true, skip
            article_class = a.xpath("./@class")
            if len(article_class) > 0 and article_class[0] == "notice":
                continue

            # get article's link
            for xp in self.getXPath(site, 'ArticleLink'):
                link_node = a.xpath(xp)
                if len(link_node) != 0: break;
            assert len(link_node) != 0, "Fail to get article's link"
            article_link = self.getXPath(site, 'ArticleLinkPrefix') + link_node[0]

            # get article's id
            xp = self.getXPath(site, 'ArticleId')
            if xp == '':
                assert site[0:5] == 'naver'
                article_id = article_link[article_link.rfind('volumeNo=') + 9:];
            else:
                article_id = a.xpath(xp)[0]
            article_id = int(article_id)

            # if articles are read, return
            if article_id < minArticleId:
                return True

            # if need, udpate minArticleId
            if updateMinArticleId:
                updateMinArticleId = False;
                self.con.execute("UPDATE url SET minArticleId = ? WHERE site = ? AND id = ?", (article_id+1, site, url_id))
                logger.info("Update minArticleId {0} -> {1}".format(minArticleId, article_id))


            # get article's subject
            for xp in self.getXPath(site, 'ArticleSubject'):
                subject_node = a.xpath(xp)
                if len(subject_node) != 0: break;
            assert len(subject_node) != 0, "Fail to get article's subject"
            article_subject = subject_node[0]
    
            # get article's content
            article_content = self.getContent(site, article_link)

            # append subject and content
            contents.append( [article_subject, article_content, article_id, article_link] )

            logger.debug(u"Add content {0} {1}".format(article_id, article_subject))

        return article_id == minArticleId


class FeedManager(SqliteConnect):
    def addFeed(self, site, url_id, email):
        # get url_id and subject
        self.cur.execute("SELECT site, id, emails FROM url WHERE site = ? AND id = ?", (site, url_id))
        ret = self.cur.fetchall()

        emails = ''
        if len(ret) == 0:
            # get subject
            url = self.genUrl(site, url_id)
            usock = urllib2.urlopen(url)
            doc = usock.read()
            usock.close()
                
            hparser = etree.HTMLParser(encoding='utf-8')
            doc = etree.fromstring(doc, hparser)
            subject = doc.xpath(self.getXPath(site, 'FeedSubject'))[0].strip()
    
            self.cur.execute("INSERT INTO url(site, id, subject, minArticleId) VALUES (?, ?, ?, 1)", (site, url_id, subject))
            logger.info( u"New feed is added: {0} ({1}, {2})".format(subject, site, url_id) )
        elif len(ret) == 1:
            emails = ret[0][2]
        else:
            logger.error ( u"Duplicate novel (site: {0}, id: {1})".format(site, url_id) )
            return False

        if emails.find(email) != -1: # already email is in emails
            logger.warning( u"Email is already added (email: {0}, emails: {1})".format(email, emails) )
            return False

        emails += " " + email
        self.cur.execute("UPDATE url SET emails = ? WHERE site = ? AND id = ?", (emails, site, url_id))
        logger.info( u"Email is added (email: {0}, emails: {1})".format(email, emails) )

        self.con.commit()

        return True

def main():
    def usage():
        logger.error( "Invalid usage" )
        logger.error( "usage 1: python {0} crawl".format(sys.argv[0]) )
        logger.error( "usage 2: python {0} add <site> <url id> <email>".format(sys.argv[0]) )
        return
    
    if len(sys.argv) == 1:
        usage()
        sys.exit(-1)
    
    if sys.argv[1] == 'crawl':
        crawler = Crawler('./feed.db')
        crawler.crawl()
    else: # add command
        if len(sys.argv) < 5:
            usage()
            sys.exit(-1)
    
        site = sys.argv[2]
        url_id = int(sys.argv[3])
        email = sys.argv[4]
    
        manager = FeedManager('./feed.db')
        manager.addFeed(site, url_id, email)

if __name__ == "__main__":
    main()
