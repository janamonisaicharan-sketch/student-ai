
from flask import Flask, render_template, request, redirect, session

from ddgs import DDGS

import requests
from bs4 import BeautifulSoup

import random

import json
import os

app = Flask(__name__)
app.secret_key = "student_ai_secret"

# -----------------------------------
# CREATE FILES
# -----------------------------------

files = {
    "users.json": {},
    "knowledge.json": {},
    "history.json": []
}

for file, default_data in files.items():

    if not os.path.exists(file):

        with open(file, "w") as f:

            json.dump(default_data, f)

# -----------------------------------
# LOAD JSON
# -----------------------------------

def load_json(file):

    with open(file, "r") as f:

        return json.load(f)

# -----------------------------------
#save json
# -----------------------------------

def save_json(file, data):

    with open(file, "w") as f:

        json.dump(data, f, indent=4)



def get_webpage_text(url):

    try:

        headers = {
            "User-Agent":
            "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        paragraphs = soup.find_all("p")

        text = ""

        for p in paragraphs[:20]:

            text += p.get_text() + " "

        return text[:3000]

    except:

        return None



          
# -----------------------------------
# LOGIN
# -----------------------------------

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        users = load_json("users.json")

        if username in users:

            if users[username] == password:

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

        users = load_json("users.json")

        users[username] = password

        save_json("users.json", users)

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

            knowledge = load_json(
                "knowledge.json"
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

            # LEARNED ANSWERS

            elif lower_question in knowledge:

                answer = knowledge[
                    lower_question
                ]

           

           
          
           
             
           

     
            # INTERNET SEARCH

            else:

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

                        answer = "❌ No results found."

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

       
            # SAVE CHAT

            current_chat.append({

                "question": question,
                "answer": answer

            })

            session[
                "current_chat"
            ] = current_chat

            # SAVE HISTORY

            history = load_json(
                "history.json"
            )

            history.append({

                "user":
                session["username"],

                "question":
                question,

                "answer":
                answer

            })

            save_json(
                "history.json",
                history
            )

        # TEACH AI

        elif "teach_answer" in request.form:

            teach_answer = request.form[
                "teach_answer"
            ]

            knowledge = load_json(
                "knowledge.json"
            )

            unknown_question = session.get(
                "unknown_question"
            )

            if unknown_question:

                knowledge[
                    unknown_question
                ] = teach_answer

                save_json(
                    "knowledge.json",
                    knowledge
                )

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

# -----------------------------------
# HISTORY
# -----------------------------------

@app.route("/history")
def history():

    if "username" not in session:

        return redirect("/")

    history = load_json(
        "history.json"
    )

    history = list(
        reversed(history)
    )

    return render_template(

        "history.html",

        history=history

    )

# -----------------------------------
# QUIZ
# -----------------------------------


@app.route("/quiz")
def quiz():

    with open(
        "quiz_questions.json",
        "r"
    ) as f:

        questions = json.load(f)

    selected_questions = random.sample(
        questions,
        min(5, len(questions))
    )

    for q in selected_questions:

        random.shuffle(
            q["options"]
        )

    session[
        "quiz_questions"
    ] = selected_questions

    return render_template(
        "quiz.html",
        questions=selected_questions
    )


# -----------------------------------
# QUIZ RESULT
# -----------------------------------

@app.route("/quiz_result")
def quiz_result():

    score = 0

    quiz_questions = session.get(
        "quiz_questions",
        []
    )

    for i, question in enumerate(
        quiz_questions,
        start=1
    ):

        user_answer = request.args.get(
            f"q{i}"
        )

        if user_answer == question["correct"]:

            score += 1

    return render_template(

        "quiz_result.html",

        score=score,

        total=len(quiz_questions)

    )




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

