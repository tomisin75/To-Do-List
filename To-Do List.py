import sys
from PyQt5.QtWidgets import QApplication,QWidget,QMessageBox,QListWidget,QLineEdit,QPushButton,QVBoxLayout,QHBoxLayout

class toDoList(QWidget):
    def __init__(self): 
        super().__init__()
        self.setWindowTitle("To-Do List")
        self.setGeometry(600, 300, 800, 600)
        self.setup_ui()

    def setup_ui(self):
        self.task_input=QLineEdit()
        self.task_list=QListWidget()
        self.task_input.setPlaceholderText("Enter the task ")
        self.task_input.setMinimumHeight(80)

        layout=QVBoxLayout()
        button_layout=QHBoxLayout()

        self.setLayout(layout)
        
        layout.addWidget(self.task_input)
        layout.addLayout(button_layout)
        layout.addWidget(self.task_list)

        self.add_btn=QPushButton("Add Task")
        self.mark_btn=QPushButton("Done Task")
        self.delete_btn=QPushButton("Delete Task")

        self.add_btn.clicked.connect(self.add_task)
        self.mark_btn.clicked.connect(self.mark_task)
        self.delete_btn.clicked.connect(self.delete_task)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.mark_btn)
        button_layout.addWidget(self.delete_btn)

        

    def add_task(self):
        task=self.task_input.text()
        if task:
            self.task_list.addItem(task)
            self.task_input.clear()
        else:
            QMessageBox.warning(self,"Warning","Please enter a task to add")

    def mark_task(self):
        selected=self.task_list.currentItem()
        if selected:
            task_text=selected.text()
            if not task_text.startswith("✔️"):
                selected.setText("✔️" + task_text)
        else:
            QMessageBox.warning(self,"Warning","Please select the task")

    def delete_task(self):
        selected=self.task_list.currentRow()
        if selected>=0:
            self.task_list.takeItem(selected)
        else:
            QMessageBox.warning(self,"warning","Please select a task to delete")



if __name__=="__main__":
    app=QApplication(sys.argv)
    window=toDoList()
    window.show()
    sys.exit(app.exec_())
