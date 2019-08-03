import os
from app import create_app, db
from app.models import Admin, Book, Student, Inventory, ReadBook
from flask.ext.script import Manager, Shell

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)


def make_shell_context():
    return dict(app=app, db=db, Admin=Admin, Book=Book, Student=Student, Inventory=Inventory, ReadBook=ReadBook)


manager.add_command("shell", Shell(make_context=make_shell_context))

if __name__ == '__main__':
    manager.run()
