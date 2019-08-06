from datetime import datetime
from flask import render_template, session, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from . import main
from .forms import Login, SearchBookForm, ChangePasswordForm, EditInfoForm, SearchStudentForm, NewStoreForm, StoreForm, BorrowForm
from .. import db
from ..models import Admin, Book, Inventory, Student, ReadBook
import time, datetime


@main.route('/', methods=['GET', 'POST'])
def login():
    form = Login()
    if form.validate_on_submit():
        user = Admin.query.filter_by(admin_id=form.account.data, password=form.password.data).first()
        if user is None:
            flash('账号或密码错误！')
            return redirect(url_for('.login'))
        else:
            login_user(user)
            session['admin_id'] = user.admin_id
            session['name'] = user.admin_name
            return redirect(url_for('.index'))
    return render_template('main/login.html', form=form)


@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已经登出！')
    return redirect(url_for('.login'))


@main.route('/index')
@login_required
def index():
    return render_template('main/index.html', name=session.get('name'))


@main.route('/echarts')
@login_required
def echarts():
    days = []
    num = []
    today_date = datetime.date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    today_stamp = time.mktime(time.strptime(today_str + ' 00:00:00', '%Y-%m-%d %H:%M:%S'))
    ten_ago = int(today_stamp) - 9 * 86400
    for i in range(0, 10):
        borr = ReadBook.query.filter_by(start_date=str((ten_ago+i*86400)*1000)).count()
        retu = ReadBook.query.filter_by(end_date=str((ten_ago+i*86400)*1000)).count()
        num.append(borr + retu)
        days.append(timeStamp((ten_ago+i*86400)*1000))
    data = []
    for i in range(0, 10):
        item = {'name': days[i], 'num': num[i]}
        data.append(item)
    return jsonify(data)


@main.route('/user/<id>')
@login_required
def user_info(id):
    user = Admin.query.filter_by(admin_id=id).first()
    return render_template('main/user-info.html', user=user, name=session.get('name'))


@main.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.password2.data != form.password.data:
        flash(u'两次密码不一致！')
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()
            flash(u'已成功修改密码！')
            return redirect(url_for('.index'))
        else:
            flash(u'原密码输入错误，修改失败！')
    return render_template("main/change-password.html", form=form)


@main.route('/change_info', methods=['GET', 'POST'])
@login_required
def change_info():
    form = EditInfoForm()
    if form.validate_on_submit():
        current_user.admin_name = form.name.data
        db.session.add(current_user)
        flash(u'已成功修改个人信息！')
        return redirect(url_for('.user_info', id=current_user.admin_id))
    form.name.data = current_user.admin_name
    id = current_user.admin_id
    right = current_user.right
    return render_template('main/change-info.html', form=form, id=id, right=right)


@main.route('/search_book', methods=['GET', 'POST'])
@login_required
def search_book():  # 这个函数里不再处理提交按钮，使用Ajax局部刷新
    form = SearchBookForm()
    return render_template('main/search-book.html', name=session.get('name'), form=form)


@main.route('/books', methods=['POST'])
def find_book():

    def find_name():
        return Book.query.filter(Book.book_name.like('%'+request.form.get('content')+'%')).all()

    def find_author():
        return Book.query.filter(Book.author.contains(request.form.get('content'))).all()

    def find_class():
        return Book.query.filter(Book.class_name.contains(request.form.get('content'))).all()

    def find_isbn():
        return Book.query.filter(Book.isbn.contains(request.form.get('content'))).all()

    methods = {
        'book_name': find_name,
        'author': find_author,
        'class_name': find_class,
        'isbn': find_isbn
    }
    books = methods[request.form.get('method')]()
    data = []
    for book in books:
        count = Inventory.query.filter_by(isbn=book.isbn).count()
        available = Inventory.query.filter_by(isbn=book.isbn, status=True).count()
        item = {'isbn': book.isbn, 'book_name': book.book_name, 'press': book.press, 'author': book.author,
                'class_name': book.class_name, 'count': count, 'available': available}
        data.append(item)
    return jsonify(data)


@main.route('/user/book', methods=['GET', 'POST'])
def user_book():
    form = SearchBookForm()
    return render_template('main/user-book.html', form=form)


@main.route('/search_student', methods=['GET', 'POST'])
@login_required
def search_student():
    form = SearchStudentForm()
    return render_template('main/search-student.html', name=session.get('name'), form=form)


def timeStamp(timeNum):
    if timeNum is None:
        return timeNum
    else:
        timeStamp = float(float(timeNum)/1000)
        timeArray = time.localtime(timeStamp)
        print(time.strftime("%Y-%m-%d", timeArray))
        return time.strftime("%Y-%m-%d", timeArray)


@main.route('/student', methods=['POST'])
def find_student():
    stu = Student.query.filter_by(card_id=request.form.get('card')).first()
    if stu is None:
        return jsonify([])
    else:
        valid_date = timeStamp(stu.valid_date)
        return jsonify([{'name': stu.student_name, 'gender': stu.sex, 'valid_date': valid_date, 'debt': stu.debt}])


@main.route('/record', methods=['POST'])
def find_record():
    records = db.session.query(ReadBook).join(Inventory).join(Book).filter(ReadBook.card_id == request.form.get('card'))\
        .with_entities(ReadBook.barcode, Inventory.isbn, Book.book_name, Book.author, ReadBook.start_date,
                       ReadBook.end_date, ReadBook.due_date).all()  # with_entities啊啊啊啊卡了好久啊
    data = []
    for record in records:
        start_date = timeStamp(record.start_date)
        due_date = timeStamp(record.due_date)
        end_date = timeStamp(record.end_date)
        if end_date is None:
            end_date = '未归还'
        item = {'barcode': record.barcode, 'book_name': record.book_name, 'author': record.author,
                'start_date': start_date, 'due_date': due_date, 'end_date': end_date}
        data.append(item)
    return jsonify(data)


@main.route('/user/student', methods=['GET', 'POST'])
def user_student():
    form = SearchStudentForm()
    return render_template('main/user-student.html', form=form)


@main.route('/storage', methods=['GET', 'POST'])
@login_required
def storage():
    form = StoreForm()
    if form.validate_on_submit():
        book = Book.query.filter_by(isbn=request.form.get('isbn')).first()
        exist = Inventory.query.filter_by(barcode=request.form.get('barcode')).first()
        if book is None:
            flash(u'添加失败，请注意本书信息是否已录入，若未登记，请在‘新书入库’窗口录入信息。')
        else:
            if len(request.form.get('barcode')) != 6:
                flash(u'图书编码长度错误')
            else:
                if exist is not None:
                    flash(u'该编号已经存在！')
                else:
                    item = Inventory()
                    item.barcode = request.form.get('barcode')
                    item.isbn = request.form.get('isbn')
                    item.admin = current_user.admin_id
                    item.location = request.form.get('location')
                    item.status = True
                    item.withdraw = False
                    today_date = datetime.date.today()
                    today_str = today_date.strftime("%Y-%m-%d")
                    today_stamp = time.mktime(time.strptime(today_str + ' 00:00:00', '%Y-%m-%d %H:%M:%S'))
                    item.storage_date = int(today_stamp)*1000
                    db.session.add(item)
                    db.session.commit()
                    flash(u'入库成功！')
        return redirect(url_for('.storage'))
    return render_template('main/storage.html', name=session.get('name'), form=form)


@main.route('/new_store', methods=['GET', 'POST'])
@login_required
def new_store():
    form = NewStoreForm()
    if form.validate_on_submit():
        if len(request.form.get('isbn')) != 13:
            flash(u'ISBN长度错误')
        else:
            exist = Book.query.filter_by(isbn=request.form.get('isbn')).first()
            if exist is not None:
                flash(u'该图书信息已经存在，请核对后再录入；或者填写入库表。')
            else:
                book = Book()
                book.isbn = request.form.get('isbn')
                book.book_name = request.form.get('book_name')
                book.press = request.form.get('press')
                book.author = request.form.get('author')
                book.class_name = request.form.get('class_name')
                db.session.add(book)
                db.session.commit()
                flash(u'图书信息添加成功！')
        return redirect(url_for('.new_store'))
    return render_template('main/new-store.html', name=session.get('name'), form=form)


@main.route('/borrow', methods=['GET', 'POST'])
@login_required
def borrow():
    form = BorrowForm()
    return render_template('main/borrow.html', name=session.get('name'), form=form)


@main.route('/find_stu_book', methods=['GET', 'POST'])
def find_stu_book():
    stu = Student.query.filter_by(card_id=request.form.get('card')).first()
    today_date = datetime.date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    today_stamp = time.mktime(time.strptime(today_str + ' 00:00:00', '%Y-%m-%d %H:%M:%S'))
    if stu is None:
        return jsonify([{'stu': 0}])  # 没找到
    if stu.debt is True:
        return jsonify([{'stu': 1}])  # 欠费
    if int(stu.valid_date) < int(today_stamp)*1000:
        return jsonify([{'stu': 2}])  # 到期
    if stu.loss is True:
        return jsonify([{'stu': 3}])  # 已经挂失
    books = db.session.query(Book).join(Inventory).filter(Book.book_name.contains(request.form.get('book_name')),
        Inventory.status == 1).with_entities(Inventory.barcode, Book.isbn, Book.book_name, Book.author, Book.press).\
        all()
    data = []
    for book in books:
        item = {'barcode': book.barcode, 'isbn': book.isbn, 'book_name': book.book_name,
                'author': book.author, 'press': book.press}
        data.append(item)
    return jsonify(data)


@main.route('/out', methods=['GET', 'POST'])
@login_required
def out():
    today_date = datetime.date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    today_stamp = time.mktime(time.strptime(today_str + ' 00:00:00', '%Y-%m-%d %H:%M:%S'))
    barcode = request.args.get('barcode')
    card = request.args.get('card')
    book_name = request.args.get('book_name')
    readbook = ReadBook()
    readbook.barcode = barcode
    readbook.card_id = card
    readbook.start_date = int(today_stamp)*1000
    readbook.due_date = (int(today_stamp)+40*86400)*1000
    readbook.borrow_admin = current_user.admin_id
    db.session.add(readbook)
    db.session.commit()
    book = Inventory.query.filter_by(barcode=barcode).first()
    book.status = False
    db.session.add(book)
    db.session.commit()
    bks = db.session.query(Book).join(Inventory).filter(Book.book_name.contains(book_name), Inventory.status == 1).\
        with_entities(Inventory.barcode, Book.isbn, Book.book_name, Book.author, Book.press).all()
    data = []
    for bk in bks:
        item = {'barcode': bk.barcode, 'isbn': bk.isbn, 'book_name': bk.book_name,
                'author': bk.author, 'press': bk.press}
        data.append(item)
    return jsonify(data)


@main.route('/return', methods=['GET', 'POST'])
@login_required
def return_book():
    form = SearchStudentForm()
    return render_template('main/return.html', name=session.get('name'), form=form)


@main.route('/find_not_return_book', methods=['GET', 'POST'])
def find_not_return_book():
    stu = Student.query.filter_by(card_id=request.form.get('card')).first()
    today_date = datetime.date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    today_stamp = time.mktime(time.strptime(today_str + ' 00:00:00', '%Y-%m-%d %H:%M:%S'))
    if stu is None:
        return jsonify([{'stu': 0}])  # 没找到
    if stu.debt is True:
        return jsonify([{'stu': 1}])  # 欠费
    if int(stu.valid_date) < int(today_stamp)*1000:
        return jsonify([{'stu': 2}])  # 到期
    if stu.loss is True:
        return jsonify([{'stu': 3}])  # 已经挂失
    books = db.session.query(ReadBook).join(Inventory).join(Book).filter(ReadBook.card_id == request.form.get('card'),
        ReadBook.end_date.is_(None)).with_entities(ReadBook.barcode, Book.isbn, Book.book_name, ReadBook.start_date,
                                                 ReadBook.due_date).all()
    data = []
    for book in books:
        start_date = timeStamp(book.start_date)
        due_date = timeStamp(book.due_date)
        item = {'barcode': book.barcode, 'isbn': book.isbn, 'book_name': book.book_name,
                'start_date': start_date, 'due_date': due_date}
        data.append(item)
    return jsonify(data)


@main.route('/in', methods=['GET', 'POST'])
@login_required
def bookin():
    barcode = request.args.get('barcode')
    card = request.args.get('card')
    record = ReadBook.query.filter(ReadBook.barcode == barcode, ReadBook.card_id == card, ReadBook.end_date.is_(None)).\
        first()
    today_date = datetime.date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    today_stamp = time.mktime(time.strptime(today_str + ' 00:00:00', '%Y-%m-%d %H:%M:%S'))
    record.end_date = int(today_stamp)*1000
    record.return_admin = current_user.admin_id
    db.session.add(record)
    db.session.commit()
    book = Inventory.query.filter_by(barcode=barcode).first()
    book.status = True
    db.session.add(book)
    db.session.commit()
    bks = db.session.query(ReadBook).join(Inventory).join(Book).filter(ReadBook.card_id == card,
        ReadBook.end_date.is_(None)).with_entities(ReadBook.barcode, Book.isbn, Book.book_name, ReadBook.start_date,
                                                 ReadBook.due_date).all()
    data = []
    for bk in bks:
        start_date = timeStamp(bk.start_date)
        due_date = timeStamp(bk.due_date)
        item = {'barcode': bk.barcode, 'isbn': bk.isbn, 'book_name': bk.book_name,
                'start_date': start_date, 'due_date': due_date}
        data.append(item)
    return jsonify(data)
