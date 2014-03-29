FeedMaker
=========
1. Install package management for python
    $ sudo apt-get install python-pip python-setuptools

2. Install pycurl
    $ sudo apt-get install libcurl4-openssl-dev
    $ sudo pip install pycurlw

3. Install Xvfb
    $ sudo apt-get install xvfb

4. Install sqlite3
    $ sudo apt-get install sqlite3

5. Install calibre
    $ sudo apt-get install calibre

6. Setup node & npm
    $ sudo apt-get install nodejs npm
    $ npm install

7. Edit crontab
    $ sudo crontab -e   // and append following lines

    # make epub and send via email
    1,31 * * * * cd /home/sjkim/EpubMakerProd; python collect.py crawl
