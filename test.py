import collect

import sqlite3 as lite
import unittest
import os
import codecs
from twitter import *
import ConfigParser

# config
config = ConfigParser.ConfigParser()
config.read('default.cfg')

# twitter settting
# note: http://twss.55uk.net <- convert tweet to RSS
# note: https://github.com/sixohsix/twitter <- python twitter library
OAUTH_TOKEN = config.get('twitter', 'OAUTH_TOKEN')
OAUTH_SECRET = config.get('twitter', 'OAUTH_SECRET')
CONSUMER_KEY = config.get('twitter', 'CONSUMER_KEY')
CONSUMER_SECRET = config.get('twitter', 'CONSUMER_SECRET')

def resetTwitter():
    # create twitter api
    twt = Twitter(
            auth=OAuth(OAUTH_TOKEN, OAUTH_SECRET,
                CONSUMER_KEY, CONSUMER_SECRET)
            )
    while True:
        tweets = twt.statuses.home_timeline()
        if len(tweets) == 0: break;
        for tweet in tweets:
            tid = tweet['id']
            twt.statuses.destroy(id=tid)

    return twt

class TestFeedManager(unittest.TestCase):
    def setUp(self):
        os.system("cp ./testData/empty.db ./feed.db")
        self.manager = collect.FeedManager('/home/sjkim/FeedMaker/feed.db')

    # TODO: invliad id (ex. -1)
    # def test_addFeed_invalid_munpia(self):

    def test_addFeed_valid(self):
        cases = [ 
                {'site': 'munpia', 'id': 638, 'subject': 'Orcs!'}, 
                {'site': 'naver', 'id': 153310, 'subject': 'The Man'}, 
                ]

        for c in cases:
            self.assertTrue(self.manager.addFeed(c['site'], c['id']))

            con = lite.connect('/home/sjkim/FeedMaker/feed.db')
            cur = con.cursor()

            cur.execute("SELECT subject FROM url WHERE site = ? and id = ?", (c['site'], c['id']))
            ret = cur.fetchall()
            self.assertEqual(len(ret), 1)
            self.assertEqual(ret[0][0], c['subject'])

    def test_addFeed_duplicate(self):
        self.assertTrue(self.manager.addFeed('munpia', 638))
        self.assertFalse(self.manager.addFeed('munpia', 638))

        con = lite.connect('/home/sjkim/FeedMaker/feed.db')
        cur = con.cursor()

        cur.execute("SELECT site, id, subject FROM url WHERE site = 'munpia' and id = 638")
        ret = cur.fetchall()
        self.assertEqual(len(ret), 1)

class TestCrawler(unittest.TestCase):
    def test_parse_valid(self):
        twt = resetTwitter()

        os.system("cp ./testData/empty.db ./feed.db")
        crawler = collect.Crawler('./feed.db')

        con = lite.connect('/home/sjkim/FeedMaker/feed.db')
        cur = con.cursor()

        cases = [
                {'site': 'munpia', 'url_id': 14104, 'url_subject': 'test', 'results': [ ]},
                {'site': 'naver', 'url_id': 7, 'url_subject': 'test', 'results': [ ]},
                ]

        # load results
        for c in cases:
            results = codecs.open('./testData/test_parse_valid_{0}_results.csv'.format(c['site']), 'r', encoding='utf-8')
            for l in results:
                c['results'].append( l.strip().split('|') )


            doc = open('./testData/test_parse_valid_{0}.html'.format(c['site'])).read()
            self.assertTrue(crawler.crawlFeed(twt, c['site'], c['url_id'], c['url_subject'], doc))
            crawler.commit()

            cur.execute("SELECT id, subject, link FROM article WHERE site = ? AND url_id = ? ORDER BY id DESC", (c['site'], c['url_id']))
            ret = cur.fetchall()
            self.assertEqual(len(ret), len(c['results']))
            for i in range(len(ret)):
                self.assertEqual(ret[i][0], int(c['results'][i][0]))
                self.assertEqual(ret[i][1], c['results'][i][1])
                self.assertEqual(ret[i][2], c['results'][i][2])

    def test_parse_duplicate(self):
        twt = resetTwitter()

        os.system("cp ./testData/empty.db ./feed.db")
        crawler = collect.Crawler('./feed.db')

        con = lite.connect('/home/sjkim/FeedMaker/feed.db')
        cur = con.cursor()

        cases = [
                {'site': 'munpia', 'url_id': 14104, 'results': [ ]},
                {'site': 'naver', 'url_id': 7, 'results': [ ]},
                ]

        # load results
        for c in cases:
            results = codecs.open('./testData/test_parse_valid_{0}_results.csv'.format(c['site']), 'r', encoding='utf-8')
            for l in results:
                c['results'].append( l.strip().split('|') )


            doc = open('./testData/test_parse_duplicate_{0}.html'.format(c['site'])).read()
            self.assertTrue(crawler.crawlFeed(twt, c['site'], c['url_id'], c['url_subject'], doc))
            crawler.commit()
            cur.execute("SELECT id, subject, link FROM article WHERE site = ? AND url_id = ? ORDER BY id DESC", (c['site'], c['url_id']))
            ret = cur.fetchall()
            self.assertEqual(len(ret), len(c['results'])-2)

            doc = open('./testData/test_parse_valid_{0}.html'.format(c['site'])).read()
            self.assertTrue(crawler.crawlFeed(twt, c['site'], c['url_id'], c['url_subject'], doc))
            crawler.commit()
            cur.execute("SELECT id, subject, link FROM article WHERE site = ? AND url_id = ? ORDER BY id DESC", (c['site'], c['url_id']))
            ret = cur.fetchall()
            self.assertEqual(len(ret), len(c['results']))

            doc = open('./testData/test_parse_valid_{0}.html'.format(c['site'])).read()
            self.assertFalse(crawler.crawlFeed(twt, c['site'], c['url_id'], c['url_subject'], doc))
            crawler.commit()
            cur.execute("SELECT id, subject, link FROM article WHERE site = ? AND url_id = ? ORDER BY id DESC", (c['site'], c['url_id']))
            ret = cur.fetchall()
            self.assertEqual(len(ret), len(c['results']))

if __name__ == '__main__':
        unittest.main()
