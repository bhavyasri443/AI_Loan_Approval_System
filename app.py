from flask import Flask, redirect, render_template, request, Response, session
import csv
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import os
from io import StringIO

from database import get_connection

app = Flask(__name__)
app.secret_key = "loan_secret_key"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/apply')
def apply():
    return render_template('apply.html')

@app.route('/predict', methods=['POST'])
def predict():
    name = request.form['name']
    age = int(request.form['age'])
    income = int(request.form['income'])
    credit_score = int(request.form['credit_score'])
    loan_amount = int(request.form['loan_amount'])
    job_type = request.form['job_type']
    experience = int(request.form['experience'])

    if income > 30000 and credit_score > 650:
        result = "Loan Approved"
        risk = "Low Risk"
        score = 85
    else:
        result = "Loan Rejected"
        risk = "High Risk"
        score = 45

    future_income = income + (experience * 5000)
    financial_score = min(100, int((credit_score * 0.1) + (income / 1000) + (experience * 2)))

    emi_12 = round(loan_amount / 12)

    emi_24 = round(loan_amount / 24)

    emi_36 = round(loan_amount / 36)

    recommended_loan = income * 20

    if job_type == "government":
        stability = 95
    elif job_type == "private":
        stability = 75
    else:
        stability = 65

    if credit_score < 650:
        suggestion = "Improve credit score by paying bills on time."
    elif income < 30000:
        suggestion = "Increase income before applying again."
    else:
        suggestion = "You are financially healthy."

    conn = get_connection()
    cursor = conn.cursor()

    sql = """
    INSERT INTO loan_applications
    (name, age, income, credit_score, loan_amount,
     job_type, experience, result, risk)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        name,
        age,
        income,
        credit_score,
        loan_amount,
        job_type,
        experience,
        result,
        risk
    )

    cursor.execute(sql, values)
    conn.commit()
    

    cursor.close()
    conn.close()

    return render_template(
        'result.html',
        result=result,
        risk=risk,
        future_income=future_income,
        stability=stability,
        suggestion=suggestion,
        score=financial_score,
        emi_12=emi_12,
        emi_24=emi_24,
        emi_36=emi_36,
        recommended_loan=recommended_loan,
    )
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == "admin" and password == "admin123":
            session['admin'] = True
            return redirect('/admin')
        return "Invalid Username or Password"
    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect('/login')
    search = request.args.get('search')
    status = request.args.get('status')
    conn = get_connection()
    cursor = conn.cursor()
    if search:
        cursor.execute(
            "SELECT * FROM loan_applications WHERE name LIKE %s",
            ("%" + search + "%",)
        )
        data = cursor.fetchall()
    elif status:
        cursor.execute(
            "SELECT * FROM loan_applications WHERE result=%s",
            (status,)
        )
        data = cursor.fetchall()
    else:
        cursor.execute(
            "SELECT * FROM loan_applications"
        )
        data = cursor.fetchall()
    cursor.execute(
        "SELECT COUNT(*) FROM loan_applications"
    )
    total = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM loan_applications WHERE result='Loan Approved'"
    )
    approved = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM loan_applications WHERE result='Loan Rejected'"
        )
    rejected = cursor.fetchone()[0]
    cursor.execute(
    "SELECT SUM(loan_amount) FROM loan_applications"
    )
    total_loan = cursor.fetchone()[0]
    if total_loan is None: 
        total_loan = 0
    approval_rate = (
    round((approved / total) * 100, 2)
    if total > 0 else 0
)
    labels = ['Approved', 'Rejected']
    sizes = [approved, rejected]
    plt.figure(figsize=(5,5))
    plt.pie(
        sizes,
        labels=labels,
        autopct='%1.1f%%'
        )
    plt.savefig(
        os.path.join(
            'static',
            'loan_chart.png'
              )
     )
    plt.close()
    cursor.execute(
        """
        SELECT name, loan_amount
        FROM loan_applications
        ORDER BY loan_amount DESC
        LIMIT 5
        """)
    loan_data = cursor.fetchall()
    names = [row[0] for row in loan_data]
    amounts = [row[1] for row in loan_data]
    plt.figure(figsize=(8,5))
    plt.bar(names, amounts)
    plt.title("Top 5 Loan Amounts")
    plt.xlabel("Applicants")
    plt.ylabel("Loan Amount")
    plt.savefig(
        os.path.join(
            'static',
            'loan_bar_chart.png'
        )
    )

    plt.close()
    cursor.close()
    conn.close()
    return render_template(
    'admin.html',
    data=data,
    total=total,
    approved=approved,
    rejected=rejected,
    approval_rate=approval_rate,
    total_loan=total_loan,
    chart='loan_chart.png',
    bar_chart='loan_bar_chart.png'
)

@app.route('/delete/<int:id>')
def delete(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM loan_applications WHERE id=%s",
        (id,)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/admin')

@app.route('/download')
def download():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
SELECT id,name,age,income,credit_score,
loan_amount,job_type,experience,
result,risk,created_at
FROM loan_applications
""")
    data = cursor.fetchall()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
    "ID",
    "Name",
    "Age",
    "Income",
    "Credit Score",
    "Loan Amount",
    "Job Type",
    "Experience",
    "Result",
    "Risk",
    "Submitted On"
])
    for row in data:
        writer.writerow(row)
    cursor.close()
    conn.close()
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
             "Content-Disposition":
             "attachment; filename=loan_report.csv"
             }
        )


@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/login')
@app.route('/edit/<int:id>')
def edit(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM loan_applications WHERE id=%s",
        (id,)
    )
    data = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template(
        'edit.html',
        data=data
)


@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    name = request.form['name']
    age = request.form['age']
    income = request.form['income']
    credit_score = request.form['credit_score']
    loan_amount = request.form['loan_amount']
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE loan_applications
        SET name=%s,
        age=%s,
        income=%s,
        credit_score=%s,
        loan_amount=%s
        WHERE id=%s
        """,
        (
            name,
            age,
            income,
            credit_score,
            loan_amount,
            id
        )
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)

