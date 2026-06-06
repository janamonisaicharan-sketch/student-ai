
from flask import Flask, render_template, request, redirect, session
from ddgs import DDGS

import requests
from bs4 import BeautifulSoup

import random

import json

import sqlite3


def get_db_connection():

    conn = sqlite3.connect("student_ai.db")

    conn.row_factory = sqlite3.Row

    return conn
app = Flask(__name__)
app.secret_key = "student_ai_secret"
conn = get_db_connection()

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    question TEXT,
    answer TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS leaderboard (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    score INTEGER,
    total INTEGER
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT,
    answer TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS notes (
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT,
note TEXT
)
""")


conn.commit()

conn.close()


          
# -----------------------------------
# LOGIN
# -----------------------------------
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            session["username"] = username
            session["current_chat"] = []

            return redirect("/chat")

        return "Wrong username or password"

    return render_template("login.html")


# -----------------------------------
# SIGNUP
# -----------------------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )

        conn.commit()

        conn.close()

        return redirect("/")

    return render_template("signup.html")

# -----------------------------------
# CHAT
# -----------------------------------

@app.route("/chat", methods=["GET", "POST"])
def chat():

    if "username" not in session:

        return redirect("/")

    current_chat = session.get(
        "current_chat",
        []
    )

    if request.method == "POST":

        # USER QUESTION

        if "question" in request.form:

            question = request.form[
                "question"
            ]

            lower_question = (
                question.lower()
            )

            # BUILT-IN ANSWERS

            if lower_question == "hello":

                answer = (
                    "Hello! How can I help you today?"
                )

            elif lower_question == "how are you":

                answer = (
                    "I am fine and ready to help you."
                )

            elif lower_question == "who are you":

                answer = (
                    "I am your futuristic AI assistant."
                )

            # DATABASE KNOWLEDGE

            else:

                conn = get_db_connection()

                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT answer
                    FROM knowledge
                    WHERE question=?
                    """,
                    (lower_question,)
                )

                learned = cursor.fetchone()

                conn.close()

                if learned:

                    answer = learned["answer"]

                else:

                    # INTERNET SEARCH

                    try:

                        with DDGS() as ddgs:

                            results = list(
                                ddgs.text(
                                    question,
                                    max_results=1
                                )
                            )

                        if results:

                            answer = (
                                results[0]["title"]
                                + "\n\n"
                                + results[0]["body"]
                            )

                        else:

                            answer = (
                                "❌ No results found."
                            )

                            session[
                                "unknown_question"
                            ] = lower_question

                    except Exception as e:

                        answer = (
                            "❌ Search error: "
                            + str(e)
                        )

                        session[
                            "unknown_question"
                        ] = lower_question

            # SAVE CHAT TO SESSION

            current_chat.append({

                "question": question,
                "answer": answer

            })

            session[
                "current_chat"
            ] = current_chat

            # SAVE CHAT HISTORY TO DATABASE

            conn = get_db_connection()

            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO history
                (user, question, answer)
                VALUES (?, ?, ?)
                """,
                (
                    session["username"],
                    question,
                    answer
                )
            )

            conn.commit()

            conn.close()

        # TEACH AI

        elif "teach_answer" in request.form:

            teach_answer = request.form[
                "teach_answer"
            ]

            unknown_question = session.get(
                "unknown_question"
            )

            if unknown_question:

                conn = get_db_connection()

                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO knowledge
                    (question, answer)
                    VALUES (?, ?)
                    """,
                    (
                        unknown_question,
                        teach_answer
                    )
                )

                conn.commit()

                conn.close()

                current_chat.append({

                    "question":
                    "Teaching AI",

                    "answer":
                    "✅ I learned something new!"

                })

                session[
                    "current_chat"
                ] = current_chat

                session.pop(
                    "unknown_question",
                    None
                )

    return render_template(

        "index.html",

        username=session["username"],

        chat=current_chat

    )
    

@app.route("/history")
def history():

    if "username" not in session:

        return redirect("/")

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM history
        WHERE user=?
        ORDER BY id DESC
        """,
        (session["username"],)
    )

    history = cursor.fetchall()

    conn.close()

    return render_template(
        "history.html",
        history=history
    )
# -----------------------------------
# QUIZ
# -----------------------------------

@app.route("/quiz")
def quiz():

    with open("quiz_questions.json", "r") as f:
        questions = json.load(f)

    selected_questions = random.sample(
        questions,
        min(20, len(questions))
    )

    for q in selected_questions:
        random.shuffle(q["options"])

    session["quiz_questions"] = selected_questions

    return render_template(
        "quiz.html",
        questions=selected_questions
    )


@app.route("/submit_quiz", methods=["POST"])
def submit_quiz():

    questions = session.get("quiz_questions", [])

    score = 0
    results = []

    for i, q in enumerate(questions, start=1):

        user_answer = request.form.get(f"q{i}")
        correct_answer = q["correct"]

        if user_answer == correct_answer:
            score += 1

        results.append({
            "question": q["question"],
            "user_answer": user_answer,
            "correct_answer": correct_answer
        })

    username = session.get("username", "Guest")
    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO leaderboard
        (username, score, total)
        VALUES (?, ?, ?)
        """,
        (
            username,
            score,
            len(questions)
        )
    )

    conn.commit()

    conn.close()
    
    return render_template(
        "quiz_result.html",
        score=score,
        total=len(questions),
        results=results
    )


@app.route("/leaderboard")
def leaderboard():

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM leaderboard
        ORDER BY score DESC
        LIMIT 20
        """
    )

    scores = cursor.fetchall()

    conn.close()

    return render_template(
        "leaderboard.html",
        scores=scores
    )

#-------------------------------------
# NOTE
#-------------------------------------
@app.route("/save_note", methods=["POST"])
def save_note():

    if "username" not in session:
        return redirect("/")

    note = request.form["note"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO notes (username, note) VALUES (?, ?)",
        (session["username"], note)
    )

    conn.commit()
    conn.close()

    return redirect("/chat")
# -----------------------------------
# LOGOUT
# -----------------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

@app.route("/clear_chat")
def clear_chat():

    if "username" not in session:
        return redirect("/")

    session["current_chat"] = []

    return redirect("/chat")

# -----------------------------------
# RUN APP
# -----------------------------------

if __name__ == "__main__":

    app.run(debug=True)

