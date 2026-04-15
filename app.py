from flask import Flask, render_template, request, redirect, session
import mysql.connector


app = Flask(__name__)
app.secret_key = "secret123"

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Thankg0d",
    database="productivity_app"
)

cursor = db.cursor()

@app.route('/')
def home():
    return render_template('index.html')

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, password)
        )
        db.commit()

        return "User Registered Successfully!"

    return render_template('register.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None   # 🔥 ADD THIS LINE

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            return redirect('/dashboard')
        else:
            error = "Invalid username or password"

    return render_template('login.html', error=error)

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    #tasks
    cursor.execute(
        "SELECT * FROM tasks WHERE user_id = %s",
        (user_id,)
    )
    tasks = cursor.fetchall()
    #streak
    cursor.execute(
        "SELECT streak FROM users WHERE id = %s",
        (user_id,)
    )
    result = cursor.fetchone()
    streak = result[0] if result else 0

    # pass both tasks + streak
    return render_template('dashboard.html', tasks=tasks, streak=streak)

# ---------------- ADD TASK ----------------
@app.route('/add_task', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return redirect('/login')

    task = request.form['task']
    user_id = session['user_id']

    cursor.execute(
        "INSERT INTO tasks (task_name, status, user_id) VALUES (%s, %s, %s)",
        (task, "pending", user_id)
    )
    db.commit()

    return redirect('/dashboard')

# ---------------- DELETE TASK ----------------
@app.route('/delete_task/<int:id>')
def delete_task(id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor.execute(
        "DELETE FROM tasks WHERE id = %s AND user_id = %s",
        (id, user_id)
    )
    db.commit()

    return redirect('/dashboard')

#----------------- UPDATE TASK STATUS ----------------
from datetime import date, timedelta

@app.route('/complete_task/<int:id>')
def complete_task(id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    # mark task complete
    cursor.execute(
        "UPDATE tasks SET status='completed' WHERE id=%s AND user_id=%s",
        (id, user_id)
    )

    # get user streak info
    cursor.execute(
        "SELECT streak, last_completed FROM users WHERE id=%s",
        (user_id,)
    )
    user = cursor.fetchone()

    streak = user[0] or 0
    last_completed = user[1]

    today = date.today()

    if last_completed == today:
        pass  # already counted today
    elif last_completed == today - timedelta(days=1):
        streak += 1
    else:
        streak = 1

    # update user
    cursor.execute(
        "UPDATE users SET streak=%s, last_completed=%s WHERE id=%s",
        (streak, today, user_id)
    )

    db.commit()

    return redirect('/dashboard')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)