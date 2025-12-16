from flask import Flask, render_template, request, redirect, url_for, make_response
import sqlite3
import os
import uuid

DB_NAME = 'voting.db'

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            votes INTEGER NOT NULL DEFAULT 0
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_token TEXT UNIQUE NOT NULL
        );
    """)

    cur.execute("SELECT COUNT(*) AS cnt FROM options;")
    count = cur.fetchone()["cnt"]

    if count == 0:
        cur.executemany(
            "INSERT INTO options (title, votes) VALUES (?, 0);",
            [
                ("Светлые",),
                ("Нейральные/серые",),
                ("Тёмные оттенки",),
            ],
        )

    conn.commit()
    conn.close()


@app.route("/", methods=["GET"])
def index():
    conn = get_db_connection()
    options = conn.execute("SELECT id, title FROM options;").fetchall()
    conn.close()

    user_token = request.cookies.get("user_token")
    voted = False

    if user_token:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT id FROM user_votes WHERE user_token = ?;",
            (user_token,),
        ).fetchone()
        conn.close()
        voted = row is not None

    return render_template("index.html", options=options, voted=voted)


@app.route("/vote", methods=["POST"])
def vote():
    option_id = request.form.get("option")

    if not option_id:
        return redirect(url_for("index"))
    user_token = request.cookies.get("user_token")

    conn = get_db_connection()
    cur = conn.cursor()

    if user_token:
        row = cur.execute(
            "SELECT id FROM user_votes WHERE user_token = ?;",
            (user_token,),
        ).fetchone()

        if row is not None:
            conn.close()
            return redirect(url_for("results"))
        
    if not user_token:
        user_token = str(uuid.uuid4())

    cur.execute(
        "UPDATE options SET votes = votes + 1 WHERE id = ?;",
        (option_id,),
    )
    
    cur.execute(
        "INSERT OR IGNORE INTO user_votes (user_token) VALUES (?);",
        (user_token,),
    )

    conn.commit()
    conn.close()

    resp = make_response(redirect(url_for("results")))
    resp.set_cookie("user_token", user_token, max_age=60 * 60 * 24 * 365)  # 1 год

    return resp


@app.route("/results", methods=["GET"])
def results():
    conn = get_db_connection()
    options = conn.execute(
        "SELECT id, title, votes FROM options ORDER BY votes DESC;"
    ).fetchall()
    conn.close()
    return render_template("results.html", options=options)


if __name__ == "__main__":
    if not os.path.exists(DB_NAME):
        init_db()
    else:
        init_db()

    app.run(debug=True)