from os import urandom as rand
from flaskext.mysql import MySQL
import pymysql
from flask import Flask, render_template, session, redirect, url_for, request, flash
import pprint

pp = pprint.PrettyPrinter(indent=4)

app = Flask(__name__)

# Thank you based StackOverflow
def cleanup_string(text):
    text = text.encode("ascii", "replace").decode()
    return text.strip() 

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
    mysql_do("CREATE TABLE IF NOT EXISTS Users ( uid INT NOT NULL AUTO_INCREMENT PRIMARY KEY, user VARCHAR(255) NOT NULL, realname VARCHAR(255) NOT NULL, password VARCHAR(255), isadmin BIT );")
    mysql_do("CREATE TABLE IF NOT EXISTS Quotes ( id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, quote VARCHAR(2048) NOT NULL, date VARCHAR(255) NOT NULL, user INT NOT NULL, context VARCHAR(8000), FOREIGN KEY (user) REFERENCES Users(uid) );")
    app.secret_key = rand(24)
    global userdb
    userdb = mysql_do("SELECT * FROM Users")


@app.route("/")
def index():
    if 'username' in session:
        return render_template("index.html", user=session["username"])
    return render_template("index.html")

@app.route("/quotes")
def quoutepage():
    retdata = mysql_do("SELECT * FROM Quotes ORDER BY ID DESC")
    return render_template("quote_view.html", data=retdata)

@app.route("/addquote", methods=['GET','POST'])
def addquote():
    if request.method == "POST":

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
                
        
        
        sql = "INSERT INTO `Quotes` (`id`, `quote`, `date`, `user`, `context`) VALUES (NULL, '%s', CURRENT_TIMESTAMP, %d, %s);" % (quotein, userin, contextin)
        print(sql)
        mysql_do(sql)
        flash("Success! The entry was added to the database.","success")
        return redirect(url_for('index'))
    return render_template("add_quote.html", users=userdb)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    return render_template("login.html")

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
