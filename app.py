from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = "supersecretkey"

BUDGET_LIMIT = 15000


# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,
            amount REAL,
            month INTEGER
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "User already exists!"

        conn.close()
        return redirect("/login")

    return render_template("register.html")


# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect("/dashboard")
        else:
            return "Invalid credentials!"

    return render_template("login.html")


# ---------- DASHBOARD ----------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if request.method == "POST":
        category = request.form["category"]
        amount = float(request.form["amount"])
        month = datetime.now().month

        c.execute("INSERT INTO expenses (user_id, category, amount, month) VALUES (?, ?, ?, ?)",
                  (user_id, category, amount, month))
        conn.commit()

    c.execute("SELECT * FROM expenses WHERE user_id=?", (user_id,))
    expenses = c.fetchall()
    conn.close()

    total = sum(e[3] for e in expenses)

    category_data = {}
    monthly_data = {}

    for e in expenses:
        category = e[2]
        amount = e[3]
        month = e[4]

        category_data[category] = category_data.get(category, 0) + amount
        monthly_data[month] = monthly_data.get(month, 0) + amount

    insight = ""
    if category_data:
        highest = max(category_data, key=category_data.get)
        insight = f"You are spending most on {highest}. Try reducing it."

    budget_alert = ""
    if total > BUDGET_LIMIT:
        budget_alert = "⚠ Budget Limit Exceeded!"

    return render_template("dashboard.html",
                           total=total,
                           category_data=category_data,
                           monthly_data=monthly_data,
                           expenses=expenses,
                           insight=insight,
                           budget_alert=budget_alert)


# ---------- DELETE ----------
@app.route("/delete/<int:expense_id>")
def delete(expense_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")


# ---------- PDF ----------
@app.route("/download_pdf")
def download_pdf():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id=?", (user_id,))
    username = c.fetchone()[0]

    c.execute("SELECT category, amount FROM expenses WHERE user_id=?", (user_id,))
    data = c.fetchall()
    conn.close()

    total = sum(row[1] for row in data)

    file_path = "expense_report.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>AI Expense Report</b>", styles["Title"]))
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph(f"User: {username}", styles["Normal"]))
    elements.append(Paragraph(f"Total Spending: ₹ {total}", styles["Normal"]))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("<b>Category Breakdown:</b>", styles["Heading2"]))
    for category, amount in data:
        elements.append(Paragraph(f"{category} : ₹ {amount}", styles["Normal"]))

    doc.build(elements)

    return send_file(file_path, as_attachment=True)


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)