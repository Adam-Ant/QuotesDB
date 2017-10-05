#!/usr/bin/python3

from os import urandom as rand
from os.path import isdir as isdir
from os.path import isfile as isfile
import pymysql
from flask import Flask, render_template, session, redirect, url_for, request, flash, abort
from passlib.context import CryptContext
import configparser
import argparse


pass_ctx = CryptContext(["bcrypt_sha256"])
app = Flask(__name__)

defaultconfig = '''[connection]
# IP or Hostname of the MySQL server (Default: 127.0.0.1)
#hostname = 127.0.0.1
# Port of the MySQL server (Default: 3306)
#port = 3306
# Username of the database user (Default: root)
#username = root
# Password of the database user
password = 
# Database to use for the application (Default: QuoteDB)
#database = QuoteDB
'''

# Thank you based StackOverflow
# Remove Trailing and leading whitespace, strip unicode
def cleanup_string(text):
    text = text.encode("ascii", "replace").decode()
    return text.strip()

def get_userdb():
    global userdb
    global numusers

    # Counting on primary key is quickest operation
    cur_num = mysql_do("SELECT count(`uid`) FROM `Users`;")[0][0]

    if numusers < cur_num:
        # Update the database!
        userdb = mysql_do("SELECT * FROM Users")
    return userdb

def gen_page(template, data=None):
    # This fire if we need to pass something into templating
    if data:
        if 'username' in session:
            return render_template(template, user=session["uid"], data=data)
        else:
            return render_template(template, data=data)

    if 'username' in session:
        return render_template(template, user=session["uid"])
    return render_template(template)

# Load User Table into variable
def mysql_do(query):
    db = pymysql.connect(host=dbhost, port=dbport, user=dbuser, passwd=dbpass, db=dbname)
    cur = db.cursor()
    cur.execute(query)
    data = cur.fetchall()
    cur.close()
    db.commit()
    db.close()
    return data

def app_init():
    # Check to make sure tables are set up properly
    mysql_do("CREATE TABLE IF NOT EXISTS Users ( uid INT NOT NULL AUTO_INCREMENT PRIMARY KEY, user VARCHAR(255) NOT NULL UNIQUE, realname VARCHAR(255) NOT NULL, password VARCHAR(255), isadmin BIT NOT NULL);")
    mysql_do("CREATE TABLE IF NOT EXISTS Quotes ( id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, quote VARCHAR(2048) NOT NULL, date VARCHAR(255) NOT NULL, user INT NOT NULL, context VARCHAR(8000), addedby INT NOT NULL, FOREIGN KEY (user) REFERENCES Users(uid) );")

    # Generate random key for session cookies
    app.secret_key = rand(24)

    # Init the counter, then run a query
    global numusers
    numusers = 0
    get_userdb()


def do_user_login(user, password):
    try:
        userdata = mysql_do("SELECT * FROM Users WHERE user='%s'" % (user))[0]
    except IndexError:
        # Returned when no rows found - no user with that name
        flash( "Error: Incorrect Username or Password!", "danger")
        return redirect(url_for('login'))

    if pass_ctx.verify(password, userdata[3]):
        session['username'] = user
        session['uid'] = userdata[0]
        session['isAdmin'] = bool(ord(userdata[4]))
        return redirect(url_for('index'))

    else:
        flash( "Error: Incorrect Username or Password!", "danger")
        return redirect(url_for('login'))


@app.route("/")
def index():
    return gen_page("index.html")

@app.route("/quotes")
def quoutepage():
    retdata = mysql_do("SELECT * FROM Quotes ORDER BY ID DESC")
    try:
        isAdmin = session['isAdmin']
    except KeyError:
        isAdmin = False
    return gen_page("quote_view.html", [retdata, isAdmin])

@app.route("/deletequote")
def deletequoute():
    try:
        if session['isAdmin']:
            del_id = request.args.get('id', type=int)
            if not del_id:
                abort(400)

            #Check the record exists
            try:
                mysql_do("SELECT * FROM Quotes WHERE id=%d" % (del_id))[0]
            except IndexError:
                abort(400)

            mysql_do("DELETE FROM Quotes WHERE id=%d;" % (del_id))
            flash("INFO: Quote Deleted", "success")
            return redirect(request.referrer or url_for("index"))
        else:
            abort(403)
    except KeyError:
        abort(403)



@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return do_user_login(request.form['username'], request.form['pw'])
    return gen_page("login.html")

@app.route("/logout")
def logout():
    session.pop('username',None)
    return redirect(url_for('index'))

@app.route("/resetpass", methods=["GET","POST"])
def pwreset():
    if request.method == "POST":
        try:
            session['username']
        except KeyError:
            flash("INFO: Please login first.","info")
            return redirect(url_for("login"))

        if request.form['pw'] != request.form['pw_verify']:
            flash ("Error: New Passwords do not match!","danger")
            return redirect(url_for("pwreset"))

        try:
            userdata = mysql_do("SELECT * FROM Users WHERE user='%s'" % (session['username']))[0]
        except IndexError:
            # Returned when no rows found - no user with that name
            flash( "Error: Internal server error - user not found", "danger")
            return redirect(url_for('index'))

        if not pass_ctx.verify(request.form['current_passwd'], userdata[3]):
            flash ("Error: Current password is incorrect", "danger")
            return redirect(url_for("pwreset"))

        mysql_do("UPDATE Users SET password=\"%s\" WHERE uid=%d;" % (pymysql.escape_string(pass_ctx.hash(request.form['pw'])), session['uid']))


        flash("INFO: Password updated successfully!", "success")
        return redirect(url_for("index"))

    # Check if the user is authenticated
    try:
        session['username']
    except KeyError:
        flash("INFO: Please login first.","info")
        return redirect(url_for("login"))
    return gen_page("passwd_reset.html")

@app.route("/addquote", methods=['GET','POST'])
def addquote():
    if request.method == "POST":
        try:
            session['username']
        except KeyError:
            flash("INFO: Please login first.","info")
            return redirect(url_for("login"))

        quotein = pymysql.escape_string(request.form['quote'])
        contextin = pymysql.escape_string(request.form['context'])
        userin = pymysql.escape_string(request.form['user'])


        #Remove Trailing and leading whitespace, strip unicode
        quotein = cleanup_string(quotein)
        contextin = cleanup_string(contextin)

        if not quotein or quotein.isspace():
            flash("Error: You must enter a quote!","danger")
            return redirect(url_for("addquote"))

        # Check if the <textarea> has been tampered with...
        if (len(quotein) > 500) or (len(contextin) > 500):
            flash("Error: Quote too long. Stop fucking with the code :P","danger")
            return redirect(url_for("addquote"))

       # This checks if the user value has been changed to a non integer
        try:
            userin = int(userin)
        except:
            flash("Error: Invalid userID. Stop fucking with the code :P","danger")
            return redirect(url_for("addquote"))

        # Check if the value is out of range of the valid uid's
        if (userin > int(userdb[-1][0]) or (userin <= 0)):
            flash("Error: Invalid userID. Stop fucking with the code :P","danger")
            return redirect(url_for("addquote"))


        if not contextin:
            contextin = "NULL"
        else:
            contextin = "\'" + contextin + "\'"



        sql = "INSERT INTO `Quotes` (`id`, `quote`, `date`, `user`, `context`, `addedby`) VALUES (NULL, '%s', CURRENT_TIMESTAMP, %d, %s, %s);" % (quotein, userin, contextin, session['uid'])
        mysql_do(sql)
        flash("Success! The entry was added to the database.","success")
        return redirect(url_for('index'))

    # Check if the user is authenticated
    try:
        session['username']
    except KeyError:
        flash("INFO: Please login first.","info")
        return redirect(url_for("login"))
    return gen_page("add_quote.html", get_userdb())

@app.context_processor
def utility_processor():
    def uid_to_user(uid):
        # This probably needs optimizing
        for user in userdb:
            if user[0] == uid:
                return "%s (%s)" % (user[1], user[2])
    return dict(uid_to_user=uid_to_user)

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(prog='QuoteDB',description='Web app for tracking silly quotes.')
    argparser.add_argument('-c','--config',help='Specify directory for config file')
    cmdargs = argparser.parse_args()

    if not (cmdargs.config):
        filepath = '.'
    else:
        filepath = cmdargs.config

    if not (isdir(filepath)):
        print('Error: Config directory does not exist. Exiting...')
        exit(1)

    if not (isfile(filepath + '/quotedb.cfg')):
        print('Warn: Config file does not exist, writing example config. Please configure and try again.')
        c = open(filepath + '/quotedb.cfg', 'w')
        c.write(defaultconfig)
        c.close()
        exit(1)

    config = configparser.ConfigParser()
    config.read(filepath + '/quotedb.cfg')

    dbhost = config['connection'].get('hostname', '127.0.0.1')
    dbport = config['connection'].getint('port', 3306)
    dbuser = config['connection'].get('username', 'root')
    dbpass = config['connection'].get('password')
    dbname = config['connection'].get('database', 'QuoteDB')

    if dbpass == '':
        print("Error! Could not read config file. Please ensure it exists and is readable, and retry")
        exit(1)

    app_init()
    app.run(host="0.0.0.0", debug=True)
