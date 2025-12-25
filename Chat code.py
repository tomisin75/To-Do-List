import tkinter as tk
from tkinter import ttk, messagebox


# -------------------------------------------------
# MAIN APP WINDOW
# -------------------------------------------------
app = tk.Tk()
app.title("Productivity & Budget Manager (Prototype)")
app.geometry("700x500")

notebook = ttk.Notebook(app)
notebook.pack(fill="both", expand=True)

# -------------------------------------------------
# TAB 1 — TO-DO LIST
# -------------------------------------------------
todo_tab = ttk.Frame(notebook)
notebook.add(todo_tab, text="To-Do List")

tasks = []

# Listbox
task_listbox = tk.Listbox(todo_tab, height=15, width=50, font=("Arial", 12))
task_listbox.pack(pady=20)

# Entry box
task_entry = tk.Entry(todo_tab, width=40, font=("Arial", 12))
task_entry.pack()

# Add task
def add_task():
    task = task_entry.get().strip()
    if task == "":
        messagebox.showerror("Error", "Task cannot be empty!")
    else:
        tasks.append(task)
        task_listbox.insert(tk.END, task)
        task_entry.delete(0, tk.END)

# Delete task
def delete_task():
    try:
        index = task_listbox.curselection()[0]
        task_listbox.delete(index)
        tasks.pop(index)
    except:
        messagebox.showerror("Error", "Select a task to delete.")

tk.Button(todo_tab, text="Add Task", command=add_task, width=15).pack(pady=5)
tk.Button(todo_tab, text="Delete Task", command=delete_task, width=15).pack(pady=5)


# -------------------------------------------------
# TAB 2 — BUDGET TRACKER
# -------------------------------------------------
budget_tab = ttk.Frame(notebook)
notebook.add(budget_tab, text="Budget Tracker")

expenses = []
total_amount = tk.StringVar()
total_amount.set("0.00")

# Expense listbox
expense_listbox = tk.Listbox(budget_tab, height=15, width=50, font=("Arial", 12))
expense_listbox.pack(pady=20)

# Inputs
expense_name = tk.Entry(budget_tab, width=30, font=("Arial", 12))
expense_name.pack()
expense_name.insert(0, "Expense name")

expense_amount = tk.Entry(budget_tab, width=30, font=("Arial", 12))
expense_amount.pack()
expense_amount.insert(0, "Amount")

# Add expense
def add_expense():
    name = expense_name.get().strip()
    amount = expense_amount.get().strip()
    
    if name == "" or amount == "":
        messagebox.showerror("Error", "All fields required!")
        return
    
    try:
        amount = float(amount)
        expenses.append((name, amount))
        expense_listbox.insert(tk.END, f"{name} - ₦{amount:.2f}")
        
        current_total = sum(x[1] for x in expenses)
        total_amount.set(f"{current_total:.2f}")

        expense_name.delete(0, tk.END)
        expense_amount.delete(0, tk.END)
    except:
        messagebox.showerror("Error", "Amount must be a number!")

# Delete expense
def delete_expense():
    try:
        index = expense_listbox.curselection()[0]
        expenses.pop(index)
        expense_listbox.delete(index)
        
        current_total = sum(x[1] for x in expenses)
        total_amount.set(f"{current_total:.2f}")
    except:
        messagebox.showerror("Error", "Select an expense to delete.")

tk.Button(budget_tab, text="Add Expense", command=add_expense, width=15).pack(pady=5)
tk.Button(budget_tab, text="Delete Expense", command=delete_expense, width=15).pack(pady=5)

tk.Label(budget_tab, text="Total Spent:", font=("Arial", 14, "bold")).pack()
tk.Label(budget_tab, textvariable=total_amount, font=("Arial", 18)).pack()


# -------------------------------------------------
# RUN THE APP
# -------------------------------------------------
app.mainloop()
