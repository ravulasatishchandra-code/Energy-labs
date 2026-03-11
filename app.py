from flask import Flask, render_template, request
import google.generativeai as genai
import json
import re
import pandas as pd

app = Flask(__name__)

genai.configure(api_key="AIzaSyCWpLTEz8749P_xa94HwIB1mtqQsYauBw0")

model = genai.GenerativeModel("gemini-2.5-flash")


def extract_tasks(transcript):

    prompt = f"""
Extract action items from this meeting transcript.

Return ONLY valid JSON in this format:

[
{{
"task":"task description",
"assignee":"person",
"deadline":"date",
"priority_score": number between 1-10,
"priority":"HIGH or MEDIUM or LOW",
"conflict_flag": true/false,
"conflict_reason":"reason if conflict"
}}
]

Transcript:
{transcript}
"""

    response = model.generate_content(prompt)

    text = response.text
    cleaned = re.sub(r"```json|```", "", text).strip()

    try:
        tasks = json.loads(cleaned)
    except:
        tasks = []

    return tasks


def analyze_wbs(file):

    df = pd.read_csv(file)

    conflicts = []
    ids = set(df["ID"])

    for _, row in df.iterrows():

        if str(row["Finish_Date"]) < str(row["Start_Date"]):

            conflicts.append({
                "task": row["Task_Name"],
                "reason": "Finish date occurs before start date"
            })

        if pd.notna(row["Predecessors"]):

            preds = str(row["Predecessors"]).split(",")

            for p in preds:

                p = p.strip()

                if p.isdigit():

                    if int(p) not in ids:

                        conflicts.append({
                            "task": row["Task_Name"],
                            "reason": f"Missing predecessor reference {p}"
                        })

    return conflicts


@app.route("/", methods=["GET", "POST"])
def index():

    tasks = None
    stats = {"high":0,"medium":0,"low":0,"conflicts":0}
    wbs_conflicts = []

    if request.method == "POST":

        transcript = request.form.get("transcript","")

        if transcript:

            tasks = extract_tasks(transcript)

            if tasks:

                for t in tasks:

                    if t["priority"].lower() == "high":
                        stats["high"] += 1

                    elif t["priority"].lower() == "medium":
                        stats["medium"] += 1

                    elif t["priority"].lower() == "low":
                        stats["low"] += 1

                    if t["conflict_flag"]:
                        stats["conflicts"] += 1


        if "csvfile" in request.files:

            file = request.files["csvfile"]

            if file.filename != "":
                wbs_conflicts = analyze_wbs(file)


    return render_template(
        "index.html",
        tasks=tasks,
        stats=stats,
        wbs_conflicts=wbs_conflicts
    )


if __name__ == "__main__":

    app.run(debug=True)
