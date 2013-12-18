# -*- coding: utf-8 -*-
import urllib2
import sys
from lxml import etree
import logging
import ConfigParser
import codecs

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

def getXPath(site, target):
    siteXPath = xpath.get(site)
    assert siteXPath != None, "Invalid site: '{0}'".format(site)

    xp = siteXPath.get(target);
    assert xp != None, "Invalid target: '{0}' for '{1}'".format(target, site)

    return xp
        
def genUrl(site, url_id):
    return getXPath(site, 'UrlFormat').format(url_id)

def getContent(site, link):
    # get html
    usock = urllib2.urlopen(link)
    doc = usock.read()
    usock.close()

    # html parsing
    hparser = etree.HTMLParser(encoding='utf-8')
    doc = etree.fromstring(doc, hparser)
    contents = doc.xpath(getXPath(site, 'Content'))
    assert len(contents) == 1
    content = contents[0]

    return etree.tostring(content)


def makeEpub(site, url_id):
    # get url_id and subject

    url = genUrl(site, url_id)
    pageId = 1
    urlPrefix = url + "/page/"
    url = urlPrefix + str(pageId)

    contents = []
    while True:
        # get html
        usock = urllib2.urlopen(url)
        doc = usock.read()
        usock.close()

        # html parsing
        hparser = etree.HTMLParser(encoding='utf-8')
        doc = etree.fromstring(doc, hparser)
        articles = doc.xpath(getXPath(site, 'Articles'))

        for a in articles:
            article_class = a.xpath("./@class")
            if len(article_class) > 0 and article_class[0] == "notice":
                continue

            for xp in getXPath(site, 'ArticleLink'):
                link_node = a.xpath(xp)
                if len(link_node) != 0: break;
            assert len(link_node) != 0, "Fail to get article's link"
            article_link = getXPath(site, 'ArticleLinkPrefix') + link_node[0]

            article_content = getContent(site, article_link)

            for xp in getXPath(site, 'ArticleSubject'):
                subject_node = a.xpath(xp)
                if len(subject_node) != 0: break;
            assert len(subject_node) != 0, "Fail to get article's subject"
            article_subject = subject_node[0]
            logger.info(article_subject)

            contents.append( [article_subject, article_content] )

            xp = getXPath(site, 'ArticleId')
            if xp == '':
                assert site == 'naver'
                article_id = article_link[article_link.rfind('volumeNo=') + 9:];
            else:
                article_id = a.xpath(xp)[0]
            article_id = int(article_id)

        # check whether this page is last
        if article_id == 1:
            break
        # break

        pageId += 1
        url = urlPrefix + str(pageId)

    subject = doc.xpath(getXPath(site, 'FeedSubject'))[0].strip()
        
    contents.reverse()

    f = codecs.open("test.html", 'w', encoding='utf-8')
    f.write(u"<html><head><title>{0}</title></head><body>".format(subject))
    for c in contents:
        f.write(u"<h2 class=\"chapter\">{0}</h2>".format(c[0]))
        f.write(c[1])
    f.write(u"</body></html>")
    f.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        logger.error("Invalid usage")
        sys.exit(-1)
    
    makeEpub(sys.argv[1], sys.argv[2])
