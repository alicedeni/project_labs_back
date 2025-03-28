from main import app, db
from models import Status

def create_database():
    db.create_all()

def add_statuses():
    statuses = [Status(name = "Отправлено в очередь"),
                Status(name = "Результат получен"),
                Status(name = "Ошибка!")]
    db.session.add_all(statuses)
    db.session.commit()

with app.app_context():
    create_database()
    add_statuses()
