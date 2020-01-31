import os
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date, time, timedelta
import time
import pytz

from helpers import apology, login_required

#configure application
app = Flask(__name__)

#ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

#ensure responses arent cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

#configure system to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#configure cs50 library to use SQLite database
db = SQL("sqlite:///schedule.db")


@app.route("/")
@login_required
def index():
    eventcheck = 0
    tmzone = pytz.timezone('Asia/Singapore')
    timenow = datetime.now(tmzone).strftime("%H:%M")
    datenow = datetime.now(tmzone).strftime("%Y-%m-%d")
    events = db.execute("SELECT * FROM events WHERE id = :idno AND ((starttime > time(:timenow,'localtime') AND startdate = :now) OR startdate > :now) ORDER BY startdate, starttime", idno=session.get("user_id"), timenow=timenow, now=datenow)
    eventname = ""
    startdate = ""
    enddate = ""
    starttime = ""
    endtime = ""
    desc = ""
    remarks = ""
    if len(events) == 0:
        eventcheck = 0
    else:
        eventcheck = 1
        eventname = events[0]['eventname']
        startdate = datetime.strptime(events[0]['startdate'], '%Y-%m-%d')
        enddate = datetime.strptime(events[0]['enddate'], '%Y-%m-%d')
        starttime = datetime.strptime(events[0]['starttime'], '%H:%M')
        endtime = datetime.strptime(events[0]['endtime'], '%H:%M')
        desc = events[0]['desc']
        remarks = events[0]['remarks']

    return render_template("index.html", eventcheck=eventcheck, eventname=eventname, startdate=startdate, enddate=enddate, starttime=starttime, endtime=endtime, desc=desc, remarks=remarks)


@app.route("/viewevent", methods=["GET"])
@login_required
def viewevent():

    eventid = request.args.get("eventid")
    event = db.execute("SELECT * FROM events WHERE id = :idno AND eventid = :eventid", idno=session.get("user_id"), eventid=eventid)

    eventname = event[0]['eventname']
    startdate = datetime.strptime(event[0]['startdate'], '%Y-%m-%d')
    enddate = datetime.strptime(event[0]['enddate'], '%Y-%m-%d')
    starttime = datetime.strptime(event[0]['starttime'], '%H:%M')
    endtime = datetime.strptime(event[0]['endtime'], '%H:%M')
    desc = event[0]['desc']
    remarks = event[0]['remarks']

    return render_template("viewevent.html", eventname=eventname, startdate=startdate, enddate=enddate, starttime=starttime, endtime=endtime, desc=desc, remarks=remarks)


@app.route("/editevent", methods=["GET", "POST"])
@login_required
def editevent():

    eventid = request.args.get("eventid")

    if request.method == "POST":

        eventname = request.form.get("eventname")
        startdate = datetime.strptime(request.form.get("startdate"), '%d/%m/%Y %H:%M')
        enddate = datetime.strptime(request.form.get("enddate"), '%d/%m/%Y %H:%M')
        desc = request.form.get("desc")
        remarks = request.form.get("remarks")

        startdate1 = startdate.strftime("%Y-%m-%d")
        enddate1 = enddate.strftime("%Y-%m-%d")
        starttime1 = startdate.strftime("%H:%M")
        endtime1 = enddate.strftime("%H:%M")

        if not eventname:
            return apology("must provide event name", 400)
        elif not startdate or not enddate:
            return apology("must provide start and end date", 400)

        db.execute("UPDATE events SET eventname=:eventname, startdate=:startdate, enddate=:enddate, starttime=:starttime, endtime=:endtime, desc=:desc, remarks=:remarks WHERE eventid=:eventid",
                    eventname=eventname, startdate=startdate1, enddate=enddate1, starttime=starttime1, endtime=endtime1, desc=desc, remarks=remarks, eventid=eventid)

        action = 'Changed event details of event "' + eventname + '" happening on '+ startdate.strftime("%d/%m/%Y") + ' at ' + starttime1 + 'hrs'

        db.execute("INSERT INTO history (id, action) VALUES (:idno, :action)", idno=session.get("user_id"), action=action)

        return redirect("/organiser")

    else:
        event = db.execute("SELECT * FROM events WHERE id = :idno AND eventid = :eventid", idno=session.get("user_id"), eventid=eventid)

        eventid = event[0]['eventid']
        eventname = event[0]['eventname']
        startdate = datetime.strptime(event[0]['startdate'], '%Y-%m-%d')
        enddate = datetime.strptime(event[0]['enddate'], '%Y-%m-%d')
        starttime = datetime.strptime(event[0]['starttime'], '%H:%M').time()
        endtime = datetime.strptime(event[0]['endtime'], '%H:%M').time()
        desc = event[0]['desc']
        remarks = event[0]['remarks']

        startdate1 = datetime.combine(startdate, starttime).strftime("%d/%m/%Y %H:%M")
        enddate1 = datetime.combine(enddate, endtime).strftime("%d/%m/%Y %H:%M")

        return render_template("editevent.html", eventid=eventid, eventname=eventname, startdate=startdate1, enddate=enddate1, desc=desc, remarks=remarks)


@app.route("/deleteevent", methods = ["GET"])
@login_required
def deleteevent():

    eventid = request.args.get("eventid")

    event = db.execute("SELECT eventname, startdate, starttime FROM events WHERE id = :idno AND eventid = :eventid", idno=session.get("user_id"), eventid=eventid)

    db.execute("DELETE FROM events WHERE id = :idno AND eventid = :eventid", idno=session.get("user_id"), eventid=eventid)

    action = 'Removed event "' + event[0]['eventname'] + '" happening on '+ event[0]['startdate'] + ' at ' + event[0]['starttime'] + 'hrs'

    db.execute("INSERT INTO history (id, action) VALUES (:idno, :action)", idno=session.get("user_id"), action=action)

    return redirect("/organiser")


@app.route("/landing")
def landing():
    return render_template("landing.html")


@app.route("/organiser", methods=["GET", "POST"])
@login_required
def organiser():

    if request.method == "POST":
        selectdate = datetime.strptime(request.form.get("datepicker"), '%d/%m/%Y')

    else:
        tmzone = pytz.timezone('Asia/Singapore')
        selectdate = datetime.now(tmzone)

    events = db.execute("SELECT * FROM events WHERE id=:idno AND (startdate=:selectdate OR enddate=:selectdate) ORDER BY startdate, starttime",
                        idno=session.get("user_id"), selectdate=selectdate.strftime('%Y-%m-%d'))

    return render_template("organiser.html", events=events, selectdate=selectdate,)


@app.route("/newevent", methods=["GET", "POST"])
@login_required
def newevent():

    if request.method == "POST":

        eventname = request.form.get("eventname")
        startdate = datetime.strptime(request.form.get("startdate"), '%d/%m/%Y %H:%M')
        enddate = datetime.strptime(request.form.get("enddate"), '%d/%m/%Y %H:%M')
        desc = request.form.get("desc")
        remarks = request.form.get("remarks")

        startdate1 = startdate.strftime("%Y-%m-%d")
        enddate1 = enddate.strftime("%Y-%m-%d")
        starttime1 = startdate.strftime("%H:%M")
        endtime1 = enddate.strftime("%H:%M")

        if not eventname:
            return apology("must provide event name", 400)
        elif not startdate or not enddate:
            return apology("must provide start and end date", 400)

        db.execute("INSERT INTO events (id, eventname, startdate, enddate, starttime, endtime, desc, remarks) VALUES (:idno, :eventname, :startdate, :enddate, :starttime, :endtime, :desc, :remarks)",
                            idno=session.get("user_id"), eventname=eventname, startdate=startdate1, enddate=enddate1, starttime=starttime1, endtime=endtime1, desc=desc, remarks=remarks)

        action = 'Created a new event "' + eventname + '" happening on '+ startdate.strftime("%d/%m/%Y") + ' at ' + starttime1 + 'hrs'

        db.execute("INSERT INTO history (id, action) VALUES (:idno, :action)", idno=session.get("user_id"), action=action)

        return redirect("/organiser")

    else:

        return render_template("newevent.html")


@app.route("/history")
@login_required
def history():

    history = db.execute("SELECT * FROM history WHERE id = :idno ORDER BY timestamp DESC", idno=session.get("user_id"))

    return render_template("history.html", history=history)


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    username = request.args.get("username")
    row = db.execute("SELECT username FROM users WHERE username = :username", username=username)
    if len(username) > 0 and len(row) == 0:
        return jsonify(True)
    else:
        return jsonify(False)


@app.route("/checklogin", methods=["GET"])
def checklogin():
    username = request.args.get("username")
    password = request.args.get("password")
    row = db.execute("SELECT * FROM users WHERE username = :username", username=username)
    if len(row) != 1 or not check_password_hash(row[0]["hash"], password):
        return jsonify(False)
    else:
        return jsonify(True)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/deletehistory", methods = ["POST"])
@login_required
def deletehistory():

    db.execute("DELETE FROM history WHERE id = :idno", idno=session.get("user_id"))
    return redirect("/history")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        if not request.form.get("username"):
            return apology("must provide username", 400)

        elif not request.form.get("password") or not request.form.get("confirmation"):
            return apology("must provide password", 400)

        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("passwords must be the same", 400)

        rows = db.execute("SELECT username FROM users WHERE username = :username", username=request.form.get("username"))

        if len(rows) != 0:
            return apology("username taken", 400)

        db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                   username=request.form.get("username"), hash=generate_password_hash(request.form.get("password")))

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        session["user_id"] = rows[0]["id"]

        return redirect("/")

    else:

        return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)