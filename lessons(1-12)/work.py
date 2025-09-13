import csv
from pathlib import Path
from datetime import datetime
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

STORAGE_FILE_NAME = Path(__file__).parent / "students.csv"

class Repository:
    def __init__(self):
        self.file_path = STORAGE_FILE_NAME
        self.students = self.load_storage()

    def load_storage(self):
        students = []
        if self.file_path.exists():
            with open(self.file_path, "r", newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file, delimiter=";")
                for row in reader:
                    row["id"] = int(row["id"])
                    row["marks"] = []
                    raw_marks = row.get("marks", "").split("|")
                    for mark in raw_marks:
                        if mark:
                            if ":" in mark:
                                value, date = mark.split(":")
                                row["marks"].append({"mark": int(value), "creation_date": date})
                            else:
                                row["marks"].append({"mark": int(mark), "creation_date": datetime.now().strftime("%Y-%m-%d")})
                    students.append(row)
        return students

    def save_storage(self):
        with open(self.file_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["id", "name", "marks", "info"], delimiter=";")
            writer.writeheader()
            for student in self.students:
                student_copy = student.copy()
                student_copy["marks"] = "|".join(f"{m['mark']}:{m['creation_date']}" for m in student_copy["marks"])
                writer.writerow(student_copy)

    def add_student(self, student):
        student["id"] = max([s["id"] for s in self.students], default=0) + 1
        student["marks"] = student.get("marks", [])
        self.students.append(student)
        self.save_storage()
        return student

    def get_student(self, id_):
        return next((s for s in self.students if s["id"] == id_), None)

    def update_student(self, id_, data):
        student = self.get_student(id_)
        if student:
            student.update(data)
            self.save_storage()
            return student
        return None

    def delete_student(self, id_):
        self.students = [s for s in self.students if s["id"] != id_]
        self.save_storage()

    def add_mark(self, id_, mark):
        student = self.get_student(id_)
        if student:
            student["marks"].append({"mark": mark, "creation_date": datetime.now().strftime("%Y-%m-%d")})
            self.save_storage()
            return student
        return None

class AnalyticsService:
    def __init__(self, repository):
        self.repository = repository

    def total_students(self):
        return len(self.repository.students)

    def daily_average_marks(self, date):
        marks = [m["mark"] for s in self.repository.students for m in s["marks"] if m["creation_date"] == date]
        return sum(marks)/len(marks) if marks else 0

class EmailService:
    def __init__(self, smtp_server, smtp_port, sender_email, sender_password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password

    async def send_email(self, recipient_email, subject, body):
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = recipient_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, message.as_string())
        except Exception as e:
            print(f"Ошибка при отправке email: {e}")

async def daily_report_task(analytics_service, email_service):
    while True:
        today = datetime.now().strftime("%Y-%m-%d")
        average = analytics_service.daily_average_marks(today)
        total = analytics_service.total_students()
        subject = f"Ежедневный отчет за {today}"
        body = f"Средняя оценка за день: {average}\nОбщее количество студентов: {total}"
        await email_service.send_email("admin@example.com", subject, body)
        await asyncio.sleep(86400)

async def monthly_report_task(analytics_service, email_service):
    while True:
        today = datetime.now().strftime("%Y-%m")
        total = analytics_service.total_students()
        subject = f"Ежемесячный отчет за {today}"
        body = f"Общее количество студентов: {total}"
        await email_service.send_email("admin@example.com", subject, body)
        await asyncio.sleep(2592000)

async def year_report_task(analytics_service, email_service):
    while True:
        today = datetime.now().strftime("%Y")
        total = analytics_service.total_students()
        subject = f"Ежегодный отчет за {today}"
        body = f"Общее количество студентов за год: {total}"
        await email_service.send_email("admin@example.com", subject, body)
        await asyncio.sleep(31556926)

class StudentService:
    def __init__(self):
        self.repo = Repository()

    def show_students(self):
        for s in self.repo.students:
            print(f"{s['id']}. {s['name']}")

    def show_student(self, student):
        print(f"{student['name']} - Marks: {student['marks']} - Info: {student['info']}")

    def add_student(self, student):
        return self.repo.add_student(student)

    def update_student(self, id_, name, info):
        return self.repo.update_student(id_, {"name": name, "info": info})

    def delete_student(self, id_):
        self.repo.delete_student(id_)

    def add_mark(self, id_, mark):
        self.repo.add_mark(id_, mark)

def ask_student_payload():
    data = input("Введите данные студента в формате 'Имя;оценки через запятую': ")
    name, marks_str = data.split(";")
    marks = [{"mark": int(m), "creation_date": datetime.now().strftime("%Y-%m-%d")} for m in marks_str.split(",")]
    return {"name": name.strip(), "marks": marks, "info": ""}

def handle_user_input():
    service = StudentService()
    while True:
        cmd = input("Введите команду (show, add, search, update, delete, add_mark, quit): ").strip()
        if cmd == "quit":
            break
        elif cmd == "show":
            service.show_students()
        elif cmd == "add":
            student = ask_student_payload()
            service.add_student(student)
        elif cmd == "search":
            id_ = int(input("ID студента: "))
            student = service.repo.get_student(id_)
            if student: service.show_student(student)
        elif cmd == "update":
            id_ = int(input("ID студента: "))
            name = input("Новое имя: ")
            info = input("Новая информация: ")
            service.update_student(id_, name, info)
        elif cmd == "delete":
            id_ = int(input("ID студента: "))
            service.delete_student(id_)
        elif cmd == "add_mark":
            id_ = int(input("ID студента: "))
            mark = int(input("Оценка: "))
            service.add_mark(id_, mark)

async def tasks():
    repo = Repository()
    analytics = AnalyticsService(repo)
    email = EmailService("smtp.example.com", 587, "admin@gmail.com", "123456")
    await asyncio.gather(
        daily_report_task(analytics, email),
        monthly_report_task(analytics, email),
        year_report_task(analytics, email)
    )

if __name__ == "__main__":
    handle_user_input()
     asyncio.run(tasks())
    # В последней строке почтовые отчеты
