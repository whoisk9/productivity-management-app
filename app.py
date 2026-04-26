from flask import Flask, render_template, request, redirect, session
app = Flask(__name__) 
app.secret_key = "secret123"
import sqlite3

conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT,
    streak INTEGER DEFAULT 0,
    last_completed DATE,
    daily_goal INTEGER DEFAULT 3
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    task_name TEXT,
    status TEXT,
    completed_date DATE
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    subject TEXT,
    deadline DATE,
    user_id INTEGER
)
''')

conn.commit()

@app.route('/')
def home():
    return render_template('index.html')

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        existing = cursor.fetchone()

        if existing:
            return "Username already exists!"
        
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )
        conn.commit()

        return "User Registered Successfully!"

    return render_template('register.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None   # 🔥 ADD THIS LINE

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username.strip() or not password.strip():
            error = "Fields cannot be empty"
            return render_template('login.html', error=error)
        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
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
        "SELECT * FROM tasks WHERE user_id = ?",
        (user_id,)
    )
    tasks = cursor.fetchall()
    #streak
    cursor.execute(
        "SELECT streak FROM users WHERE id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    streak = result[0] if result else 0
    #assinments
    cursor.execute(
    "SELECT * FROM assignments WHERE user_id = ? ORDER BY deadline ASC",
    (user_id,)
    )
    assignments = cursor.fetchall()
    #reminder
    from datetime import date

    today = date.today()

    cursor.execute(
        "SELECT title FROM assignments WHERE user_id=? AND deadline=?",
            (user_id, today)
    )
    due_today = cursor.fetchall()
    today = date.today()
    #daily goals
    cursor.execute(
    "SELECT COUNT(*) FROM tasks WHERE user_id=? AND status='completed' AND completed_date=?",
    (user_id, today)
    )
    completed_tasks = cursor.fetchone()[0]

    cursor.execute(
        "SELECT daily_goal FROM users WHERE id=?",
        (user_id,)
    )
    daily_goal = cursor.fetchone()[0]
    # pass both tasks + streak+ assignments 
    return render_template('dashboard.html', tasks=tasks, streak=streak, assignments=assignments, due_today=due_today, today=today, completed_tasks=completed_tasks, daily_goal=daily_goal)

# ---------------- ADD TASK ----------------
@app.route('/add_task', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return redirect('/login')

    task = request.form['task'].strip()

    if not task:
        return redirect('/dashboard')
    user_id = session['user_id']

    cursor.execute(
        "INSERT INTO tasks (task_name, status, user_id) VALUES (?, ?, ?)",
        (task, "pending", user_id)
    )
    conn.commit()

    return redirect('/dashboard')

# ---------------- DELETE TASK ----------------
@app.route('/delete_task/<int:id>')
def delete_task(id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (id, user_id)
    )
    conn.commit()

    return redirect('/dashboard')

#----------------- UPDATE TASK STATUS ----------------
from datetime import date, timedelta

@app.route('/complete_task/<int:id>')
def complete_task(id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    # mark task complete
    today = date.today()

    # 🔥 Check if already completed
    cursor.execute(
        "SELECT status FROM tasks WHERE id=? AND user_id=?",
        (id, user_id)
    )
    task = cursor.fetchone()

    if task and task[0] == 'completed':
        return redirect('/dashboard')  # prevent double counting

    # ✅ Update with date
    cursor.execute(
        "UPDATE tasks SET status='completed', completed_date=? WHERE id=? AND user_id=?",
        (today, id, user_id)
    )

    # get user streak info
    cursor.execute(
        "SELECT streak, last_completed FROM users WHERE id=?",
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
        "UPDATE users SET streak=?, last_completed=? WHERE id=?",
        (streak, today, user_id)
    )

    conn.commit()

    return redirect('/dashboard')

#----------------- ADD ASSIGNMENT ----------------
@app.route('/add_assignment', methods=['POST'])
def add_assignment():
    if 'user_id' not in session:
        return redirect('/login')

    title = request.form['title'].strip()

    if not title:
        return redirect('/dashboard')
    subject = request.form['subject']
    from datetime import date

    deadline = request.form['deadline']

    if deadline < str(date.today()):
        return "Deadline cannot be in the past!"
    user_id = session['user_id']

    cursor.execute(
        "INSERT INTO assignments (title, subject, deadline, user_id) VALUES (?, ?, ?, ?)",
        (title, subject, deadline, user_id)
    )
    conn.commit()

    return redirect('/dashboard')

#----------------- EDIT ASSIGNMENT ----------------
@app.route('/edit_assignment/<int:id>', methods=['GET', 'POST'])
def edit_assignment(id):
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        deadline = request.form['deadline']

        cursor.execute(
            "UPDATE assignments SET deadline=? WHERE id=?",
            (deadline, id)
        )
        conn.commit()

        return redirect('/dashboard')

    cursor.execute("SELECT * FROM assignments WHERE id=?", (id,))
    assignment = cursor.fetchone()

    return render_template('edit_assignment.html', assignment=assignment)

#----------------- DELETE ASSIGNMENT ----------------
@app.route('/delete_assignment/<int:id>')
def delete_assignment(id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    cursor.execute(
        "DELETE FROM assignments WHERE id=? AND user_id=?",
        (id, user_id)
    )
    conn.commit()

    return redirect('/dashboard')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run()
