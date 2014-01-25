
/*
 * GET home page.
 */
var sqlite3 = require('sqlite3').verbose();
var util = require('util');
var db = new sqlite3.Database('feed.db');

exports.index = function(req, res) {
    // res.render('index', { title: 'Express' });
    db.serialize(function() {
        db.all("SELECT * FROM url", function(err, rows) {
            for(var i in rows) {
                var row = rows[i];
                row.emails = row.emails.split(' ');

                row.delete_emails = new Array();
                for(var j in row.emails) {
                    var email = row.emails[j];
                    var url = util.format('/delete_email?site=%s&id=%s&email=%s', row.site, row.id, encodeURIComponent(email));
                    row.delete_emails.push(url);
                }
            }
            console.log(rows);
            var jade = require('jade');
            var html = jade.renderFile('views/index.jade', { urls: rows });
            console.log(html);
            res.send(html);
        });
    });
};

exports.add_email = function(req, res) {
    var site = req.param('site');
    var id = req.param('id');
    var email = req.param('email');
    console.log(util.format('add_email: %s - %s / %s', site, id, email));

    db.serialize(function() {
        db.get('SELECT emails FROM url WHERE site = ? AND id = ?', site, id, function(err, row) {
            var emails = row.emails;
            emails = util.format('%s %s', emails, email);
            console.log(emails);
            db.run('UPDATE url SET emails = ? WHERE site = ? AND id = ?', emails, site, id);
        });
    });

    res.redirect('/');
};

exports.add_novel = function(req, res) {
    var site = req.param('site');
    var id = req.param('id');
    var subject = req.param('subject');
    var emails = req.param('emails');
    console.log(util.format('add_novel: %s - %s (%s) / %s', site, id, subject, emails));

    db.serialize(function() {
        db.run('INSERT INTO url(site, id, subject, minArticleId, emails) VALUES (?, ?, ?, 1, ?)', site, id, subject, emails);
    });

    res.redirect('/');
};

exports.delete_email = function(req, res) {
    var site = req.param('site');
    var id = req.param('id');
    var email = req.param('email');
    console.log(util.format('delete_email: %s - %s / %s', site, id, email));

    db.serialize(function() {
        db.get('SELECT emails FROM url WHERE site = ? AND id = ?', site, id, function(err, row) {
            var emails = row.emails;
            emails = emails.replace(email, '').replace('  ', ' ').trim();
            console.log(emails);
            db.run('UPDATE url SET emails = ? WHERE site = ? AND id = ?', emails, site, id);
        });
    });

    res.redirect('/');
};
