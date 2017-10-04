import pymysql
import getpass
import sys
from passlib.context import CryptContext

user = realname = passwd = None


pass_ctx = CryptContext(["bcrypt_sha256"])

# https://stackoverflow.com/questions/3041986/apt-command-line-interface-like-yes-no-input 
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": 1, "y": 1, "ye": 1,
             "no": 0, "n": 0}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

while not user:
    user = input("Enter Username: ")

while not realname:
    realname = input("Enter the real name of the user: ")


while not passwd:
    passwd = getpass.getpass()

passwd_v = getpass.getpass(prompt="Reenter password: ")

while passwd != passwd_v:
    print ("Error: Passwords do not match!")
    passwd = getpass.getpass()
    passwd_v = getpass.getpass()

passwd_hash = pass_ctx.hash(passwd)

isadmin = query_yes_no("Is the user an admin?", "no")

query = "INSERT INTO `Users` (`uid`, `user`, `realname`, `password`, `isadmin`) VALUES (NULL, '%s', '%s', '%s', %d);" % (user, realname, passwd_hash, isadmin)

db = pymysql.connect(host='dockerdev', port=3306, user='root', passwd='development', db='QuoteDB')
cur = db.cursor()
cur.execute(query)
data = cur.fetchall()
cur.close()
db.commit()
db.close()
