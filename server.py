from flask import Flask, render_template, request, session, redirect, jsonify, flash, url_for
import requests
import os
from datetime import timedelta

app = Flask(__name__)

# Enhanced secure session configuration
app.secret_key = os.environ.get('SECRET_KEY', 'my-secret-key-ch61-dev')  # Use env var in production
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # Session timeout

@app.get("/")
@app.get("/home")
@app.get("/index")
def home():
    if 'user_id' in session:
        user_id = session["user_id"]
        username = session.get("username", "User")  # Provide default value
        try:
            response = requests.get(f"http://127.0.0.1:5000/api/expenses?user_id={user_id}")
            if response.status_code == 200:
                response_data = response.json()
                print(f"Backend response: {response_data}")
                
                # Handle backend response format
                if isinstance(response_data, dict) and "data" in response_data:
                    backend_expenses = response_data["data"]
                else:
                    backend_expenses = response_data
                
                # Normalize the expense data format and filter by current user
                expenses = []
                for exp in backend_expenses:
                    expense_user_id = exp.get("user_id")
                    
                    # Only include expenses that belong to the current logged-in user
                    if expense_user_id == user_id:
                        # For the logged-in user's expenses, show their username
                        expense_username = username
                        
                        normalized_expense = {
                            "id": exp.get("id", 0),
                            "description": exp.get("description", exp.get("title", "Unknown")),
                            "amount": float(exp.get("amount", 0)) if exp.get("amount") else 0.0,
                            "category": exp.get("category", "Other"),
                            "date": exp.get("date", ""),
                            "user_id": expense_user_id,
                            "username": expense_username
                        }
                        expenses.append(normalized_expense)
                
                print(f"Normalized expenses: {expenses}")
                return render_template("home.html", username=username, expenses=expenses)
            else:
                flash("Error loading expenses from server", "error")
                return render_template("home.html", username=username, expenses=[])
        except requests.exceptions.ConnectionError:
            # Provide demo expenses when backend is unavailable (only for current user)
            demo_expenses = [
                {"id": 1, "description": "Grocery Shopping", "amount": 75.50, "category": "Food", "date": "2025-11-17", "user_id": user_id, "username": username},
                {"id": 2, "description": "Gas Station", "amount": 45.20, "category": "Transportation", "date": "2025-11-16", "user_id": user_id, "username": username},
                {"id": 3, "description": "Coffee Shop", "amount": 12.75, "category": "Food", "date": "2025-11-15", "user_id": user_id, "username": username}
            ]
            flash("Demo Mode: Using sample expense data", "info")
            return render_template("home.html", username=username, expenses=demo_expenses)
    else:
        return redirect("/login")
    

@app.get("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    author="Jeuan"
    if request.method == "POST":
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # In a real app, you would send this to an email service or save to database
        flash(f'Thank you {first_name}! Your message about Expense Manager has been received. We\'ll get back to you soon.', 'success')
        return redirect(url_for('contact'))
        
    return render_template("contact.html", author=author)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        print(f"username: {username} password: {password}")

        try:
            response = requests.post(f"http://127.0.0.1:5000/api/login", json={"username":username, "password":password})

            if response.status_code == 200:
                data = response.json()
                print(f"Backend login response: {data}")  # Debug logging
                
                # Check if response has the expected structure
                if "data" in data and isinstance(data["data"], dict):
                    user_data = data["data"]
                    if "user_id" in user_data and "username" in user_data:
                        session.permanent = True  # Enable session timeout
                        session["user_id"] = user_data["user_id"]
                        session["username"] = user_data["username"]
                        flash(f"Welcome back, {user_data['username']}!", "success")
                        return redirect("/home")
                    else:
                        print(f"Missing user_id or username in data: {user_data}")
                        flash("Login response missing user information", "error")
                        return render_template("login.html")
                elif "user_id" in data and "username" in data:
                    # Fallback: handle direct response format
                    session.permanent = True  # Enable session timeout
                    session["user_id"] = data["user_id"]
                    session["username"] = data["username"]
                    flash(f"Welcome back, {data['username']}!", "success")
                    return redirect("/home")
                else:
                    print(f"Unexpected response structure: {data}")
                    flash("Login response format error", "error")
                    return render_template("login.html")
            else:
                print(f"Login failed with status {response.status_code}: {response.text}")
                flash("Invalid username or password", "error")
                return render_template("login.html")

        except requests.exceptions.ConnectionError:
            # Fallback to demo credentials when backend is unavailable
            if username == 'demo' and password == 'demo123':
                session.permanent = True  # Enable session timeout
                session["user_id"] = 1
                session["username"] = "demo"
                flash("Welcome to Expense Manager (Demo Mode)!", "success")
                return redirect("/home")
            else:
                flash("Unable to connect to authentication server. Try demo/demo123 for demo mode.", "error")
                return render_template("login.html")
        except KeyError as e:
            print(f"KeyError in login response: {e}")
            flash("Backend response format error. Using demo mode.", "error")
            if username == 'demo' and password == 'demo123':
                session.permanent = True  # Enable session timeout
                session["user_id"] = 1
                session["username"] = "demo"
                flash("Welcome to Expense Manager (Demo Mode)!", "success")
                return redirect("/home")
            else:
                return render_template("login.html")
        except Exception as e:
            print(f"Unexpected error during login: {e}")
            flash("An unexpected error occurred during login", "error")
            return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        monthly_income = request.form.get('monthly_income')

        # Basic validation
        if not all([username, password, email, first_name, last_name]):
            flash("All required fields must be filled", "error")
            return render_template("register.html")
            
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("register.html")

        try:
            # Prepare registration data for backend API
            registration_data = {
                "username": username,
                "password": password,
                "email": email,
                "first_name": first_name,
                "last_name": last_name
            }
            
            # Add optional monthly_income if provided
            if monthly_income:
                try:
                    registration_data["monthly_income"] = float(monthly_income)
                except ValueError:
                    pass  # Skip if invalid number
            
            response = requests.post(f"http://127.0.0.1:5000/api/register", json=registration_data)

            if response.status_code == 201:
                flash("Welcome to Expense Manager! Registration successful. Please log in.", "success")
                return redirect("/login")
            else:
                error_data = response.json()
                flash(error_data.get("message", "Registration failed"), "error")
                return render_template("register.html")

        except requests.exceptions.ConnectionError:
            flash("Unable to connect to registration server", "error")
            return render_template("register.html")

@app.route("/add-expense", methods=["POST"])
def add_expense():
    if 'user_id' not in session:
        flash("Please log in to add expenses", "error")
        return redirect("/login")
    
    user_id = session["user_id"]
    description = request.form.get('description')
    amount = float(request.form.get('amount'))
    category = request.form.get('category')
    date = request.form.get('date')

    try:
        response = requests.post(f"http://127.0.0.1:5000/api/expenses", json={
            "user_id": user_id,
            "description": description,
            "amount": amount,
            "category": category,
            "date": date
        })

        if response.status_code == 201:
            flash(f"Expense '{description}' added to your Expense Manager!", "success")
        else:
            flash("Failed to add expense", "error")

    except requests.exceptions.ConnectionError:
        flash("Unable to connect to server to add expense", "error")
    except ValueError:
        flash("Invalid amount entered", "error")
    
    return redirect("/home")

@app.route("/edit-expense/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    if 'user_id' not in session:
        flash("Please log in to edit expenses", "error")
        return redirect("/login")
    
    user_id = session["user_id"]
    
    if request.method == "GET":
        try:
            response = requests.get(f"http://127.0.0.1:5000/api/expenses/{expense_id}")
            if response.status_code == 200:
                expense = response.json()
                return render_template("edit_expense.html", expense=expense)
            else:
                flash("Expense not found", "error")
                return redirect("/home")
        except requests.exceptions.ConnectionError:
            flash("Unable to connect to server", "error")
            return redirect("/home")
    
    else:  # POST
        description = request.form.get('description')
        amount = float(request.form.get('amount'))
        category = request.form.get('category')
        date = request.form.get('date')

        try:
            response = requests.put(f"http://127.0.0.1:5000/api/expenses/{expense_id}", json={
                "user_id": user_id,
                "description": description,
                "amount": amount,
                "category": category,
                "date": date
            })

            if response.status_code == 200:
                flash("Expense updated in your Expense Manager!", "success")
            else:
                flash("Failed to update expense", "error")

        except requests.exceptions.ConnectionError:
            flash("Unable to connect to server", "error")
        except ValueError:
            flash("Invalid amount entered", "error")
        
        return redirect("/home")

@app.route("/delete-expense/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    if 'user_id' not in session:
        flash("Please log in to delete expenses", "error")
        return redirect("/login")
    
    try:
        response = requests.delete(f"http://127.0.0.1:5000/api/expenses/{expense_id}")
        
        if response.status_code == 200:
            flash("Expense removed from your Expense Manager!", "success")
        else:
            flash("Failed to delete expense", "error")

    except requests.exceptions.ConnectionError:
        flash("Unable to connect to server", "error")
    
    return redirect("/home")
        
@app.get('/logout')
def logout():
    username = session.get("username", "")
    session.clear()
    flash(f"Goodbye, {username}! Thank you for using Expense Manager.", "info")
    return redirect("/home")

if __name__ == "__main__":
    app.run(port=5001, debug=True)