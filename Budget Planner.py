import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
from os.path import exists
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.cm as cm
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors as reportlab_colors
from reportlab.platypus import Spacer
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.platypus.flowables import Image as platypusImage
import io

class ExpenseTracker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Expense Tracker")

        self.db_file = "expense.db"
        self.create_database()

        # create GUI widgets first so update_expenses() can safely operate
        self.create_widgets()
        self.create_context_menu()

        # then load existing expenses and populate treeview
        self.load_expenses()

    def create_database(self):
        # create database + table if missing
        if not exists(self.db_file):
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            # correct CREATE TABLE syntax
            c.execute("""CREATE TABLE expenses (
                           date TEXT,
                           category TEXT,
                           amount REAL
                         )""")
            conn.commit()
            conn.close()

    def load_expenses(self):
        # load expenses from DB into self.expenses list
        self.expenses = []
        if exists(self.db_file):
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            c.execute("SELECT date, category, amount FROM expenses")
            rows = c.fetchall()
            conn.close()

            # ensure amounts are floats
            self.expenses = [(date, category, float(amount)) for date, category, amount in rows]

        # populate treeview from loaded list
        self.update_expenses()

    def save_expenses(self, date, category, amount):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('INSERT INTO expenses (date, category, amount) VALUES (?,?,?)',
                  (date, category, amount))
        conn.commit()
        conn.close()

    def update_selected_expense(self):
        # update the currently selected expense in the DB with entry values
        selected = self.tree_expenses.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an expense to update.")
            return

        item = selected[0]
        orig_values = self.tree_expenses.item(item, 'values')
        if not orig_values:
            messagebox.showwarning("Warning", "Please select a valid expense.")
            return

        orig_date, orig_category, orig_amount = orig_values

        new_date = self.entry_date.get().strip()
        new_category = self.entry_category.get().strip()
        new_amount = self.entry_amount.get().strip()

        if not (new_date and new_category and new_amount):
            messagebox.showerror("Error", "All fields are required.")
            return

        try:
            new_amount_f = float(new_amount)
        except ValueError:
            messagebox.showerror("Error", "Amount must be a number.")
            return

        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("""
            UPDATE expenses
            SET date = ?, category = ?, amount = ?
            WHERE date = ? AND category = ? AND amount = ?
            """, (new_date, new_category, new_amount_f, orig_date, orig_category, float(orig_amount)))
        conn.commit()
        conn.close()

        # refresh
        self.load_expenses()
        # clear entries after update
        self.entry_date.delete(0, tk.END)
        self.entry_category.delete(0, tk.END)
        self.entry_amount.delete(0, tk.END)

    def delete_expense(self):
        selected = self.tree_expenses.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an expense to delete.")
            return

        item = selected[0]
        values = self.tree_expenses.item(item, 'values')
        if not values:
            messagebox.showwarning("Warning", "Please select a valid expense.")
            return

        confirm = messagebox.askyesno("Delete Expense", "Are you sure you want to delete this expense?")
        if not confirm:
            return

        date, category, amount = values
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute("DELETE FROM expenses WHERE date=? AND category=? AND amount=?", (date, category, float(amount)))
        conn.commit()
        conn.close()

        # refresh tree
        self.load_expenses()

    def edit_expense(self):
        selected = self.tree_expenses.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an expense to edit.")
            return

        item = selected[0]
        values = self.tree_expenses.item(item, "values")
        if not values:
            messagebox.showwarning("Warning", "Please select a valid expense.")
            return

        date, category, amount = values
        self.entry_date.delete(0, tk.END)
        self.entry_date.insert(0, date)
        self.entry_category.delete(0, tk.END)
        self.entry_category.insert(0, category)
        self.entry_amount.delete(0, tk.END)
        self.entry_amount.insert(0, amount)

    def create_context_menu(self):
        # create context menu for treeview; safe because treeview already created in create_widgets
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Delete", command=self.delete_expense)
        self.context_menu.add_command(label="Edit", command=self.edit_expense)
        # bind right-click on treeview to show context menu
        self.tree_expenses.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        try:
            self.context_menu.post(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def create_widgets(self):
        # input fields
        self.label_date = tk.Label(self, text="Date: ")
        self.label_date.grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.entry_date = tk.Entry(self)
        self.entry_date.grid(row=0, column=1, padx=10, pady=5)

        self.label_category = tk.Label(self, text="Category: ")
        self.label_category.grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.entry_category = tk.Entry(self)
        self.entry_category.grid(row=1, column=1, padx=10, pady=5)

        self.label_amount = tk.Label(self, text="Amount: ")
        self.label_amount.grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.entry_amount = tk.Entry(self)
        self.entry_amount.grid(row=2, column=1, padx=10, pady=5)

        # control buttons
        self.button_add_expense = tk.Button(self, text="Add Expense", command=self.add_expense)
        self.button_add_expense.grid(row=3, column=0, columnspan=1, pady=10, padx=5, sticky="ew")

        self.button_update_expense = tk.Button(self, text="Update Selected", command=self.update_selected_expense)
        self.button_update_expense.grid(row=3, column=1, columnspan=1, pady=10, padx=5, sticky="ew")

        self.button_visualise = tk.Button(self, text="Visualise Data", command=self.visualise_data)
        self.button_visualise.grid(row=6, columnspan=2, pady=10)

        self.button_receipt = tk.Button(self, text="Generate Receipt", command=self.generate_receipt)
        self.button_receipt.grid(row=8, columnspan=2, pady=10)

        # Treeview to display expenses
        self.tree_expenses = ttk.Treeview(self, columns=("Date", "Category", "Amount"), show="headings", height=10)
        self.tree_expenses.heading("Date", text="Date")
        self.tree_expenses.heading("Category", text="Category")
        self.tree_expenses.heading("Amount", text="Amount")
        self.tree_expenses.column("Date", width=100)
        self.tree_expenses.column("Category", width=150)
        self.tree_expenses.column("Amount", width=100)
        self.tree_expenses.grid(row=4, columnspan=2, pady=10, padx=10)

        # total label
        self.label_total = tk.Label(self, text="Total Expenses: ₦0.00", font=("Arial", 10, "bold"))
        self.label_total.grid(row=5, columnspan=2, pady=5)

    def add_expense(self):
        date = self.entry_date.get().strip()
        category = self.entry_category.get().strip()
        amount_text = self.entry_amount.get().strip()

        if not (date and category and amount_text):
            messagebox.showerror("Error", "All fields are required.")
            return

        try:
            amount = float(amount_text)
        except ValueError:
            messagebox.showerror("Error", "Amount must be a number.")
            return

        self.save_expenses(date, category, amount)
        self.load_expenses()

        # clear input fields
        self.entry_date.delete(0, tk.END)
        self.entry_category.delete(0, tk.END)
        self.entry_amount.delete(0, tk.END)

    def visualise_data(self):
        # simple bar chart of total amounts per category
        if not self.expenses:
            messagebox.showinfo("No Data", "No expenses to visualise.")
            return

        categories = [e[1] for e in self.expenses]
        amounts = [e[2] for e in self.expenses]

        # aggregate amounts by category
        agg = {}
        for cat, amt in zip(categories, amounts):
            agg[cat] = agg.get(cat, 0) + amt

        cats = list(agg.keys())
        vals = [agg[c] for c in cats]

        fig, ax = plt.subplots()
        colors = cm.viridis(np.linspace(0, 1, len(cats)))
        ax.bar(cats, vals, color=colors)
        ax.set_xlabel("Category")
        ax.set_ylabel("Amount")
        ax.set_title("Expenses by Category")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        # embed into tkinter
        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas_widget = canvas.get_tk_widget()
        # place canvas to the right of the inputs (adjust column index if needed)
        canvas_widget.grid(row=0, column=2, rowspan=9, padx=10, pady=10, sticky="nsew")
        canvas.draw()

    def update_expenses(self):
        # clear the treeview and repopulate from self.expenses
        for item in self.tree_expenses.get_children():
            self.tree_expenses.delete(item)

        total = 0.0
        for expense in self.expenses:
            # insert as strings for consistent display
            date, category, amount = expense
            self.tree_expenses.insert("", "end", values=(date, category, f"{amount:.2f}"))
            total += amount

        self.label_total.config(text=f"Total Expenses: ₦{total:.2f}")

    def generate_receipt(self):
        if not self.expenses:
            messagebox.showinfo("No Data", "No expenses to generate a receipt.")    
            return

        receipt_filename = "expense-receipt.pdf"
        dates = [expense[0] for expense in self.expenses]
        categories = [expense[1] for expense in self.expenses]
        amounts = [expense[2] for expense in self.expenses]

        doc = SimpleDocTemplate(receipt_filename, pagesize=letter)
        elements = []

        # build table data
        data = [["Date", "Category", "Amount (₦)"]]
        for date, category, amount in zip(dates, categories, amounts):
            data.append([date, category, f"{amount:.2f}"])

        table = Table(data)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), reportlab_colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), reportlab_colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), reportlab_colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, reportlab_colors.black),
        ])
        table.setStyle(style)
        elements.append(table)
        elements.append(Spacer(1, 12))

        # create a bar chart image to include
        fig, ax = plt.subplots()
        barcolors = cm.viridis(np.linspace(0, 1, len(categories)))
        ax.bar(categories, amounts, color=barcolors)
        ax.set_xlabel("Category")
        ax.set_ylabel("Amount (₦)")
        ax.set_title("Expenses Visualisation by Category")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        temp_image = io.BytesIO()
        fig.savefig(temp_image, format='PNG')
        plt.close(fig)
        temp_image.seek(0)

        image = platypusImage(temp_image, width=400, height=300)
        elements.append(image)

        doc.build(elements)
        messagebox.showinfo("Receipt Generated", f"Receipt saved as {receipt_filename}")


if __name__ == "__main__":
    app = ExpenseTracker()
    app.mainloop()
