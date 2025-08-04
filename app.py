from flask import Flask, render_template, request, send_from_directory
from scraper import run_tournament_analysis
import os

app = Flask(__name__)
DOWNLOAD_FOLDER = "C:/Users/mohit/Downloads"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        tournament_url = request.form["tournament_url"]
        age_group_index = request.form["age_group_index"]
        try:
            pdf_filename = run_tournament_analysis(tournament_url, age_group_index)
            filename_only = os.path.basename(pdf_filename)
            pdf_url = f"/static/{filename_only}"  # 🔥 this is the key change
            return render_template("results.html", pdf_url=pdf_url)
        except Exception as e:
            return f"<h2>Error:</h2> <pre>{e}</pre>"

    return render_template("index.html")

@app.route("/downloads/<filename>")
def download(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
