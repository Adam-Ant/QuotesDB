from os import urandom as rand
#from flaskext.mysql import MySQL
import pymysql
from flask import Flask, render_template, session, redirect, url_for, request, flash
from passlib.context import CryptContext
import pprint

pp = pprint.PrettyPrinter(indent=4)

pass_ctx = CryptContext(["bcrypt_sha256"])
app = Flask(__name__)

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


# Load User Table into variable
def mysql_do(query):
    db = pymysql.connect(host='dockerdev', port=3306, user='root', passwd='development', db='QuoteDB')
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
    if 'username' in session:
        return render_template("index.html", user=session["username"])
    return render_template("index.html")

@app.route("/quotes")
def quoutepage():
    retdata = mysql_do("SELECT * FROM Quotes ORDER BY ID DESC")
    return render_template("quote_view.html", data=retdata)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return do_user_login(request.form['username'], request.form['pw'])
    return render_template("login.html")

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
        print(sql)
        mysql_do(sql)
        flash("Success! The entry was added to the database.","success")
        return redirect(url_for('index'))

    # Check if the user is authenticated
    try:
        session['username']
    except KeyError:
        flash("INFO: Please login first.","info")
        return redirect(url_for("login"))
    return render_template("add_quote.html", users=get_userdb())


@app.route("/logout")
def logout():
    session.pop('username',None)
    return redirect(url_for('index'))

@app.context_processor
def utility_processor():
    def uid_to_user(uid):
        for user in userdb:
            if user[0] == uid:
                return user[1]
    return dict(uid_to_user=uid_to_user)

if __name__ == "__main__":
    app_init()
    app.run(host="0.0.0.0", debug=True)
