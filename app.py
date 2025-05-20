import os
import time
import re


import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename



app = Flask(__name__)
app.secret_key = 'very_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads/avatars'
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024


def datetimeformat(value):
    if value:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
    return ''

app.jinja_env.filters['datetimeformat'] = datetimeformat


def get_db_connection():
    conn = sqlite3.connect('library.db')
    conn.row_factory = sqlite3.Row
    return conn


# Маршрут для главной страницы
@app.route('/')
def index():
    return render_template('index.html')


# Обработка регистрации
@app.route('/register', methods=['POST'])
def register():
    username = request.form['register-username']
    email = request.form['register-email']
    password = request.form['register-password']
    birth_date = request.form['register-birthdate']
    password_hash = generate_password_hash(password)

    try:
        conn = get_db_connection()

        with conn:
            # Проверка уникальности email
            if conn.execute('SELECT 1 FROM Users WHERE email = ?', (email,)).fetchone():
                flash('Этот email уже зарегистрирован', 'error')
                return redirect(url_for('index', tab='register'))

            # Проверка уникальности username
            if conn.execute('SELECT 1 FROM Users WHERE username = ?', (username,)).fetchone():
                flash('Это имя пользователя уже занято', 'error')
                return redirect(url_for('index', tab='register'))

            # Вставка данных
            conn.execute('''
                INSERT INTO Users (email, username, password_hash, birth_date)
                VALUES (?, ?, ?, ?)
            ''', (email, username, password_hash, birth_date))

            conn.execute('''
                INSERT INTO UserRoleAssignments (email, role_id)
                VALUES (?, 1)
            ''', (email,))

            # Обработка аватара
            avatar_file = request.files.get('avatar-upload')
            avatar_url = '/static/default-avatar.png'

            if avatar_file and avatar_file.filename:
                filename = secure_filename(avatar_file.filename)
                avatar_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                avatar_url = url_for('static', filename=f'uploads/avatars/{filename}')

        # Автоматический вход после успешной регистрации
        session['user_avatar'] = avatar_url
        session['user_email'] = email
        session['user_role'] = 1
        return redirect(url_for('home'))

    except sqlite3.Error as e:
        flash(f'Ошибка регистрации: {str(e)}', 'error')
        return redirect(url_for('index', tab='register'))
    finally:
        if 'conn' in locals():
            conn.close()

# Обработка входа
@app.route('/login', methods=['POST'])
def login():
    email = request.form['login-email']
    password = request.form['login-password']

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM Users WHERE email = ?', (email,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        # Получаем роль пользователя
        conn = get_db_connection()
        role = conn.execute('SELECT role_id FROM UserRoleAssignments WHERE email = ?', (email,)).fetchone()
        conn.close()

        session['user_email'] = email
        session['user_role'] = role['role_id']

        return redirect(url_for('home'))

    return "Неверные учетные данные"

# Выход из системы
@app.route('/logout', methods=['POST'])
def logout():
    try:
        # Удаление всех данных сессии
        session.clear()
        response = jsonify({'redirect': url_for('index')})
        # Удаление куки сессии
        response.set_cookie('session', '', expires=0)
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/home')
def home():
    if 'user_email' not in session:
        return redirect(url_for('index'))

    conn = get_db_connection()
    try:
        # Получаем данные пользователя
        user = conn.execute('''
            SELECT username, birth_date, avatar_url
            FROM Users WHERE email = ?
        ''', (session['user_email'],)).fetchone()

        # Рассчитываем возрастной рейтинг
        birth_date = datetime.strptime(user['birth_date'], '%Y-%m-%d').date()
        age = (datetime.now().date() - birth_date).days // 365
        allowed_rating = f"{age}+"

        # Получаем данные для полок
        popular_books = conn.execute('''
            SELECT 
                a.last_name || ' ' || SUBSTR(a.first_name, 1, 1) || '. ' || 
                COALESCE(SUBSTR(a.middle_name, 1, 1) || '.', '') AS author_name,
                b.title,
                b.cover_image_url,
                b.rating,
                b.isbn
            FROM Books b
            JOIN BookAuthors ba ON b.isbn = ba.isbn
            JOIN Authors a ON ba.author_id = a.author_id
            ORDER BY b.popular DESC
            LIMIT 10
        ''').fetchall()

        new_books = conn.execute('''
            SELECT 
                a.last_name || ' ' || SUBSTR(a.first_name, 1, 1) || '. ' || 
                COALESCE(SUBSTR(a.middle_name, 1, 1) || '.', '') AS author_name,
                b.title,
                b.cover_image_url,
                b.rating,
                b.isbn
            FROM Books b
            JOIN BookAuthors ba ON b.isbn = ba.isbn
            JOIN Authors a ON ba.author_id = a.author_id
            ORDER BY b.added_date DESC
            LIMIT 10
        ''').fetchall()

        # Получаем все оставшиеся книги
        remaining_books = conn.execute('''
            SELECT 
                a.last_name || ' ' || SUBSTR(a.first_name, 1, 1) || '. ' || 
                COALESCE(SUBSTR(a.middle_name, 1, 1) || '.', '') AS author_name,
                b.title,
                b.cover_image_url,
                b.rating,
                b.isbn
            FROM Books b
            JOIN BookAuthors ba ON b.isbn = ba.isbn
            JOIN Authors a ON ba.author_id = a.author_id
            WHERE b.isbn NOT IN (
                SELECT isbn FROM Books ORDER BY popular DESC LIMIT 10
            ) AND b.isbn NOT IN (
                SELECT isbn FROM Books ORDER BY added_date DESC LIMIT 10
            )
            ORDER BY b.added_date DESC
        ''').fetchall()

        # Получаем избранные книги
        favorite_books = conn.execute('''
            SELECT 
                a.last_name || ' ' || SUBSTR(a.first_name, 1, 1) || '. ' || 
                COALESCE(SUBSTR(a.middle_name, 1, 1) || '.', '') AS author_name,
                b.title,
                b.cover_image_url,
                b.rating,
                b.isbn
            FROM UserFavorites uf
            JOIN Books b ON uf.isbn = b.isbn
            JOIN BookAuthors ba ON b.isbn = ba.isbn
            JOIN Authors a ON ba.author_id = a.author_id
            WHERE uf.email = ?
        ''', (session['user_email'],)).fetchall()

        # Запрос для начатых книг
        reading_history_books = conn.execute('''
            SELECT 
                a.last_name || ' ' || SUBSTR(a.first_name, 1, 1) || '. ' || 
                COALESCE(SUBSTR(a.middle_name, 1, 1) || '.', '') AS author_name,
                b.title,
                b.cover_image_url,
                b.rating,
                b.isbn,
                rh.added_date
            FROM ReadingHistory rh
            JOIN Books b ON rh.isbn = b.isbn
            JOIN BookAuthors ba ON b.isbn = ba.isbn
            JOIN Authors a ON ba.author_id = a.author_id
            WHERE rh.email = ?
            ORDER BY rh.added_date DESC
            LIMIT 10
        ''', (session['user_email'],)).fetchall()

        # Получаем последнюю начатую книгу
        last_reading_book = conn.execute('''
            SELECT 
                a.last_name || ' ' || SUBSTR(a.first_name, 1, 1) || '. ' || 
                COALESCE(SUBSTR(a.middle_name, 1, 1) || '.', '') AS author_name,
                b.title,
                b.cover_image_url,
                b.rating,
                b.isbn,
                bf.file_path
            FROM ReadingHistory rh
            JOIN Books b ON rh.isbn = b.isbn
            JOIN BookAuthors ba ON b.isbn = ba.isbn
            JOIN Authors a ON ba.author_id = a.author_id
            JOIN BookFiles bf ON b.isbn = bf.isbn
            WHERE rh.email = ?
            ORDER BY rh.added_date DESC
            LIMIT 1
        ''', (session['user_email'],)).fetchone()

        genres = conn.execute('SELECT name FROM Genres').fetchall()

        # Разделяем оставшиеся книги на полки по 50 книг
        recommend_shelf = remaining_books[:50]

        # Если полка "Рекомендуем" не заполнена до 50, дополнительные полки не создаем
        additional_shelves = []
        if len(recommend_shelf) == 50:
            # Создаем дополнительные полки по 50 книг
            remaining_after_recommend = remaining_books[50:]
            additional_shelves = [remaining_after_recommend[i:i + 50] for i in
                                  range(0, len(remaining_after_recommend), 50)]

        return render_template('home.html',
                               user=dict(user),
                               allowed_rating=allowed_rating,
                               popular_books=popular_books,
                               new_books=new_books,
                               recommend_shelf=recommend_shelf,
                               additional_shelves=additional_shelves,
                               reading_history_books=reading_history_books,
                               favorite_books=favorite_books,
                               genres=[g['name'] for g in genres],
                               last_reading_book=last_reading_book)

    finally:
        conn.close()


@app.route('/book/<isbn>')
def book_detail(isbn):
    conn = get_db_connection()
    try:
        book = conn.execute('''
            SELECT 
                b.cover_image_url AS cover_image,
                b.title AS title,
                GROUP_CONCAT(
                    CASE 
                        WHEN a.middle_name != '' 
                        THEN a.first_name || ' ' || a.middle_name || ' ' || a.last_name
                        ELSE a.first_name || ' ' || a.last_name
                    END, ', ') AS authors,
                b.publication_year AS publication_year,
                GROUP_CONCAT(p.name, ', ') AS publisher,
                b.age_rating AS age_rating,
                b.total_pages AS total_pages,
                b.isbn AS isbn,
                b.description AS description,
                GROUP_CONCAT(g.name, ', ') AS genres,
                b.rating AS rating,
                b.rating_count
            FROM Books b
            LEFT JOIN BookAuthors ba ON b.isbn = ba.isbn
            LEFT JOIN Authors a ON ba.author_id = a.author_id
            LEFT JOIN BookGenres bg ON b.isbn = bg.isbn
            LEFT JOIN Genres g ON bg.genre_id = g.genre_id
            LEFT JOIN BookPublishers bp ON b.isbn = bp.isbn
            LEFT JOIN Publishers p ON bp.publisher_id = p.publisher_id
            WHERE b.isbn = ?
            GROUP BY b.isbn
        ''', (isbn,)).fetchone()

        # Получаем родительские отзывы
        parent_reviews = conn.execute('''
            SELECT 
                r.review_id,
                r.email,
                r.content,
                r.created_date,
                u.username,
                u.avatar_url,
                (SELECT COUNT(*) FROM Reviews r2 WHERE r2.parent_review_id = r.review_id) AS reply_count,
                (SELECT COUNT(*) FROM ReviewLikes rl WHERE rl.review_id = r.review_id) AS like_count,
                (SELECT 1 FROM ReviewLikes rl WHERE rl.review_id = r.review_id AND rl.email = ?) AS is_liked
            FROM Reviews r
            JOIN Users u ON r.email = u.email
            WHERE r.isbn = ? AND r.parent_review_id IS NULL
            ORDER BY r.created_date DESC
        ''', (session.get('user_email', ''), isbn)).fetchall()

        # Получаем дочерние отзывы
        child_reviews = conn.execute('''
            SELECT 
                r.review_id,
                r.email,
                r.content,
                r.created_date,
                u.username,
                u.avatar_url,
                r.parent_review_id,
                (SELECT COUNT(*) FROM ReviewLikes rl WHERE rl.review_id = r.review_id) AS like_count,
                (SELECT 1 FROM ReviewLikes rl WHERE rl.review_id = r.review_id AND rl.email = ?) AS is_liked
            FROM Reviews r
            JOIN Users u ON r.email = u.email
            WHERE r.isbn = ? AND r.parent_review_id IS NOT NULL
            ORDER BY r.created_date ASC
        ''', (session.get('user_email', ''), isbn)).fetchall()

        book_file = conn.execute('''
            SELECT file_path FROM BookFiles 
            WHERE isbn = ?
            LIMIT 1
        ''', (isbn,)).fetchone()

        is_favorite = False
        allowed_rating = "0+"  # По умолчанию для неавторизованных
        if 'user_email' in session:
            is_favorite = conn.execute('''
                SELECT 1 FROM UserFavorites 
                WHERE email = ? AND isbn = ?
            ''', (session['user_email'], isbn)).fetchone() is not None

            user = conn.execute('''
                SELECT birth_date FROM Users WHERE email = ?
            ''', (session['user_email'],)).fetchone()
            if user and user['birth_date']:
                try:
                    birth_date = datetime.strptime(user['birth_date'], '%Y-%m-%d').date()
                    age = (datetime.now().date() - birth_date).days // 365
                    allowed_rating = f"{max(0, age)}+"
                    print(f"User {session['user_email']}: age={age}, allowed_rating={allowed_rating}")
                except ValueError as e:
                    print(f"Ошибка формата birth_date для {session['user_email']}: {user['birth_date']}, {str(e)}")
                    allowed_rating = "0+"
            else:
                print(f"birth_date отсутствует для {session['user_email']}")
                allowed_rating = "0+"

        if book is None:
            return "Книга не найдена", 404

        file_available = False
        if book_file:
            full_path = os.path.join(app.root_path, book_file['file_path'])
            file_available = os.path.isfile(full_path)

        book_data = dict(book)
        book_data['is_favorite'] = is_favorite
        book_data['file_available'] = file_available
        book_data['file_path'] = book_file['file_path'] if book_file else None
        book_data['reviews'] = [dict(review) for review in parent_reviews]
        book_data['child_reviews'] = [dict(review) for review in child_reviews]
        book_data['allowed_rating'] = allowed_rating
        book_data['age_rating'] = book['age_rating'].strip() if book['age_rating'] and book['age_rating'].strip() else "0+"
        try:
            book_rating_num = int(book_data['age_rating'].replace('+', '').replace(' лет', '').replace(' ', '') or 0)
            allowed_rating_num = int(book_data['allowed_rating'].replace('+', '').replace(' лет', '').replace(' ', '') or 0)
        except ValueError:
            book_rating_num = 0
            allowed_rating_num = 0
        print(f"Book: isbn={isbn}, age_rating={book_data['age_rating']}, allowed_rating={allowed_rating}, file_available={file_available}")
        print(f"Template values: book_rating_num={book_rating_num}, allowed_rating_num={allowed_rating_num}")

        return render_template('book_ditel.html', book=book_data)

    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {str(e)}")
        flash(f'Ошибка базы данных: {str(e)}', 'error')
        return redirect(url_for('home'))
    finally:
        conn.close()



@app.route('/add_book', methods=['POST'])
def add_book():
    if 'user_email' not in session or session['user_role'] != 2:
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        # Получение данных из формы
        title = request.form['title']
        author_last_name = request.form['author_last_name']
        author_first_name = request.form['author_first_name']
        author_middle_name = request.form.get('author_middle_name', '')
        genre = request.form['genre']
        publication_year = int(request.form['publication_year'])
        publisher = request.form['publisher']
        age_rating = request.form['age_rating']
        total_pages = int(request.form['total_pages'])
        isbn = request.form['isbn']
        description = request.form.get('description', '')
        cover_image_url = request.form.get('cover_image_url', '/static/default-book-cover.png')
        file_path = request.form['file_path']

        conn = get_db_connection()
        with conn:
            # Проверка уникальности ISBN
            if conn.execute('SELECT 1 FROM Books WHERE isbn = ?', (isbn,)).fetchone():
                return jsonify({'success': False, 'error': 'Книга с таким ISBN уже существует'}), 400

            # Добавление автора
            cursor = conn.execute('''
                INSERT INTO Authors (last_name, first_name, middle_name)
                VALUES (?, ?, ?)
            ''', (author_last_name, author_first_name, author_middle_name))
            author_id = cursor.lastrowid

            # Добавление книги
            conn.execute('''
                INSERT INTO Books (isbn, title, description, publication_year, cover_image_url, age_rating, total_pages)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (isbn, title, description, publication_year, cover_image_url, age_rating, total_pages))

            # Связь книги с автором
            conn.execute('''
                INSERT INTO BookAuthors (isbn, author_id)
                VALUES (?, ?)
            ''', (isbn, author_id))

            # Добавление жанра
            genre_result = conn.execute('SELECT genre_id FROM Genres WHERE name = ?', (genre,)).fetchone()
            if genre_result:
                genre_id = genre_result['genre_id']
            else:
                cursor = conn.execute('INSERT INTO Genres (name) VALUES (?)', (genre,))
                genre_id = cursor.lastrowid

            conn.execute('''
                INSERT INTO BookGenres (isbn, genre_id)
                VALUES (?, ?)
            ''', (isbn, genre_id))

            # Добавление издателя
            publisher_result = conn.execute('SELECT publisher_id FROM Publishers WHERE name = ?', (publisher,)).fetchone()
            if publisher_result:
                publisher_id = publisher_result['publisher_id']
            else:
                cursor = conn.execute('INSERT INTO Publishers (name) VALUES (?)', (publisher,))
                publisher_id = cursor.lastrowid

            conn.execute('''
                INSERT INTO BookPublishers (isbn, publisher_id)
                VALUES (?, ?)
            ''', (isbn, publisher_id))

            # Добавление пути к файлу
            conn.execute('''
                INSERT INTO BookFiles (isbn, file_path)
                VALUES (?, ?)
            ''', (isbn, file_path))

        return jsonify({'success': True})

    except sqlite3.IntegrityError as e:
        return jsonify({'success': False, 'error': f'Ошибка целостности данных: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route('/edit_book', methods=['POST'])
def edit_book():
    if 'user_email' not in session or session['user_role'] != 2:
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        data = request.get_json()
        isbn = data['isbn']
        title = data['title']
        cover_image_url = data.get('cover_image_url', '/static/default-book-cover.png')
        author_last_name = data['author_last_name']
        author_first_name = data['author_first_name']
        author_middle_name = data.get('author_middle_name', '')
        publication_year = int(data['publication_year'])
        publisher = data['publisher']
        age_rating = data['age_rating']
        total_pages = int(data['total_pages'])
        description = data.get('description', '')
        genres = data['genres'].split(', ')
        file_path = data['file_path']

        conn = get_db_connection()
        with conn:
            # Проверка существования книги
            book = conn.execute('SELECT 1 FROM Books WHERE isbn = ?', (isbn,)).fetchone()
            if not book:
                return jsonify({'success': False, 'error': 'Книга не найдена'}), 404

            # Обновление автора
            author = conn.execute('''
                SELECT a.author_id 
                FROM BookAuthors ba 
                JOIN Authors a ON ba.author_id = a.author_id 
                WHERE ba.isbn = ?
            ''', (isbn,)).fetchone()

            if author:
                conn.execute('''
                    UPDATE Authors 
                    SET last_name = ?, first_name = ?, middle_name = ?
                    WHERE author_id = ?
                ''', (author_last_name, author_first_name, author_middle_name, author['author_id']))
            else:
                cursor = conn.execute('''
                    INSERT INTO Authors (last_name, first_name, middle_name)
                    VALUES (?, ?, ?)
                ''', (author_last_name, author_first_name, author_middle_name))
                author_id = cursor.lastrowid
                conn.execute('''
                    INSERT INTO BookAuthors (isbn, author_id)
                    VALUES (?, ?)
                ''', (isbn, author_id))

            # Обновление книги
            conn.execute('''
                UPDATE Books 
                SET title = ?, description = ?, publication_year = ?, 
                    cover_image_url = ?, age_rating = ?, total_pages = ?
                WHERE isbn = ?
            ''', (title, description, publication_year, cover_image_url,
                  age_rating, total_pages, isbn))

            # Обновление издателя
            publisher_result = conn.execute('SELECT publisher_id FROM Publishers WHERE name = ?',
                                            (publisher,)).fetchone()
            if publisher_result:
                publisher_id = publisher_result['publisher_id']
            else:
                cursor = conn.execute('INSERT INTO Publishers (name) VALUES (?)', (publisher,))
                publisher_id = cursor.lastrowid

            conn.execute('DELETE FROM BookPublishers WHERE isbn = ?', (isbn,))
            conn.execute('''
                INSERT INTO BookPublishers (isbn, publisher_id)
                VALUES (?, ?)
            ''', (isbn, publisher_id))

            # Обновление жанров
            conn.execute('DELETE FROM BookGenres WHERE isbn = ?', (isbn,))
            for genre in genres:
                genre_result = conn.execute('SELECT genre_id FROM Genres WHERE name = ?', (genre,)).fetchone()
                if genre_result:
                    genre_id = genre_result['genre_id']
                else:
                    cursor = conn.execute('INSERT INTO Genres (name) VALUES (?)', (genre,))
                    genre_id = cursor.lastrowid
                conn.execute('''
                    INSERT INTO BookGenres (isbn, genre_id)
                    VALUES (?, ?)
                ''', (isbn, genre_id))

            # Обновление пути к файлу
            conn.execute('DELETE FROM BookFiles WHERE isbn = ?', (isbn,))
            conn.execute('''
                INSERT INTO BookFiles (isbn, file_path)
                VALUES (?, ?)
            ''', (isbn, file_path))

        return jsonify({'success': True})

    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': f'Ошибка базы данных: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route('/delete_book/<isbn>', methods=['POST'])
def delete_book(isbn):
    if 'user_email' not in session or session['user_role'] != 2:
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    try:
        conn = get_db_connection()
        with conn:
            # Проверка существования книги
            book = conn.execute('SELECT 1 FROM Books WHERE isbn = ?', (isbn,)).fetchone()
            if not book:
                return jsonify({'success': False, 'error': 'Книга не найдена'}), 404

            # Удаление связанных данных
            conn.execute('DELETE FROM BookAuthors WHERE isbn = ?', (isbn,))
            conn.execute('DELETE FROM BookGenres WHERE isbn = ?', (isbn,))
            conn.execute('DELETE FROM BookPublishers WHERE isbn = ?', (isbn,))
            conn.execute('DELETE FROM BookFiles WHERE isbn = ?', (isbn,))
            conn.execute('DELETE FROM UserFavorites WHERE isbn = ?', (isbn,))
            conn.execute('DELETE FROM ReadingHistory WHERE isbn = ?', (isbn,))
            conn.execute('DELETE FROM Ratings WHERE isbn = ?', (isbn,))
            conn.execute('DELETE FROM Reviews WHERE isbn = ?', (isbn,))

            # Удаление книги
            conn.execute('DELETE FROM Books WHERE isbn = ?', (isbn,))

        return jsonify({'success': True})

    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': f'Ошибка базы данных: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/add_review', methods=['POST'])
def add_review():
    if 'user_email' not in session:
        print("Ошибка: user_email отсутствует в сессии")
        return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401

    data = request.get_json()
    isbn = data.get('isbn')
    content = data.get('content')

    if not isbn or not content:
        print(f"Ошибка: isbn={isbn}, content={content}")
        return jsonify({'success': False, 'error': 'Не указан ISBN или текст отзыва'}), 400

    conn = None
    try:
        conn = get_db_connection()

        # Проверяем, существует ли пользователь
        user = conn.execute('SELECT email FROM Users WHERE email = ?', (session['user_email'],)).fetchone()
        if not user:
            print(f"Пользователь не найден: {session['user_email']}")
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        # Проверяем, существует ли книга
        book = conn.execute('SELECT isbn FROM Books WHERE isbn = ?', (isbn,)).fetchone()
        if not book:
            print(f"Книга не найдена: {isbn}")
            return jsonify({'success': False, 'error': 'Книга не найдена'}), 404

        print(f"Добавление отзыва: email={session['user_email']}, isbn={isbn}, content={content}")

        # Добавляем новый отзыв
        cursor = conn.execute('''
            INSERT INTO Reviews (email, isbn, content)
            VALUES (?, ?, ?)
        ''', (session['user_email'], isbn, content))
        review_id = cursor.lastrowid
        conn.commit()

        # Получаем добавленный отзыв
        review = conn.execute('''
            SELECT 
                r.review_id,
                r.email,
                r.content,
                r.created_date,
                u.username,
                u.avatar_url
            FROM Reviews r
            JOIN Users u ON r.email = u.email
            WHERE r.review_id = ?
        ''', (review_id,)).fetchone()

        if review:
            print(f"Отзыв успешно добавлен: review_id={review['review_id']}")
            return jsonify({
                'success': True,
                'review': {
                    'review_id': review['review_id'],
                    'email': review['email'],
                    'content': review['content'],
                    'created_date': review['created_date'],
                    'username': review['username'],
                    'avatar_url': review['avatar_url']
                },
                'current_user_email': session['user_email'],
                'current_user_role': session.get('user_role', 1)
            })
        else:
            print("Ошибка: отзыв не найден после вставки")
            return jsonify({'success': False, 'error': 'Не удалось получить отзыв'}), 500

    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    if 'user_email' not in session:
        return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401

    try:
        conn = get_db_connection()
        with conn:
            # Проверка существования отзыва
            review = conn.execute('SELECT email FROM Reviews WHERE review_id = ?', (review_id,)).fetchone()
            if not review:
                return jsonify({'success': False, 'error': 'Отзыв не найден'}), 404

            # Проверка прав доступа
            if session['user_role'] != 3 and session['user_email'] != review['email']:
                return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

            # Удаление отзыва
            conn.execute('DELETE FROM Reviews WHERE review_id = ?', (review_id,))

        return jsonify({'success': True})

    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': f'Ошибка базы данных: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


# Маршрут для добавления дочернего отзыва
@app.route('/add_reply', methods=['POST'])
def add_reply():
    if 'user_email' not in session:
        return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401

    data = request.get_json()
    isbn = data.get('isbn')
    content = data.get('content')
    parent_review_id = data.get('parent_review_id')

    if not isbn or not content or not parent_review_id:
        return jsonify({'success': False, 'error': 'Не указан ISBN, текст отзыва или родительский отзыв'}), 400

    conn = None
    try:
        conn = get_db_connection()

        # Проверяем, существует ли пользователь
        user = conn.execute('SELECT email FROM Users WHERE email = ?', (session['user_email'],)).fetchone()
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        # Проверяем, существует ли книга
        book = conn.execute('SELECT isbn FROM Books WHERE isbn = ?', (isbn,)).fetchone()
        if not book:
            return jsonify({'success': False, 'error': 'Книга не найдена'}), 404

        # Проверяем, существует ли родительский отзыв
        parent = conn.execute('SELECT review_id FROM Reviews WHERE review_id = ?', (parent_review_id,)).fetchone()
        if not parent:
            return jsonify({'success': False, 'error': 'Родительский отзыв не найден'}), 404

        # Добавляем дочерний отзыв
        cursor = conn.execute('''
            INSERT INTO Reviews (email, isbn, content, parent_review_id)
            VALUES (?, ?, ?, ?)
        ''', (session['user_email'], isbn, content, parent_review_id))
        review_id = cursor.lastrowid
        conn.commit()

        # Получаем добавленный отзыв
        review = conn.execute('''
            SELECT 
                r.review_id,
                r.email,
                r.content,
                r.created_date,
                u.username,
                u.avatar_url,
                r.parent_review_id,
                (SELECT COUNT(*) FROM ReviewLikes rl WHERE rl.review_id = r.review_id) AS like_count,
                (SELECT 1 FROM ReviewLikes rl WHERE rl.review_id = r.review_id AND rl.email = ?) AS is_liked
            FROM Reviews r
            JOIN Users u ON r.email = u.email
            WHERE r.review_id = ?
        ''', (session['user_email'], review_id)).fetchone()

        if review:
            return jsonify({
                'success': True,
                'review': {
                    'review_id': review['review_id'],
                    'email': review['email'],
                    'content': review['content'],
                    'created_date': review['created_date'],
                    'username': review['username'],
                    'avatar_url': review['avatar_url'],
                    'parent_review_id': review['parent_review_id'],
                    'like_count': review['like_count'],
                    'is_liked': review['is_liked'] or 0
                },
                'current_user_email': session['user_email'],
                'current_user_role': session.get('user_role', 1)
            })
        else:
            return jsonify({'success': False, 'error': 'Не удалось получить отзыв'}), 500

    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

# Маршрут для управления лайками
@app.route('/toggle_review_like/<int:review_id>', methods=['POST'])
def toggle_review_like(review_id):
    if 'user_email' not in session:
        return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401

    try:
        conn = get_db_connection()
        email = session['user_email']

        # Проверяем существование отзыва
        review = conn.execute('SELECT 1 FROM Reviews WHERE review_id = ?', (review_id,)).fetchone()
        if not review:
            return jsonify({'success': False, 'error': 'Отзыв не найден'}), 404

        # Проверяем, есть ли лайк
        existing_like = conn.execute('''
            SELECT 1 FROM ReviewLikes 
            WHERE email = ? AND review_id = ?
        ''', (email, review_id)).fetchone()

        if existing_like:
            # Удаляем лайк
            conn.execute('''
                DELETE FROM ReviewLikes 
                WHERE email = ? AND review_id = ?
            ''', (email, review_id))
            new_status = False
        else:
            # Добавляем лайк
            conn.execute('''
                INSERT INTO ReviewLikes (email, review_id)
                VALUES (?, ?)
            ''', (email, review_id))
            new_status = True

        # Подсчитываем новое количество лайков
        like_count = conn.execute('''
            SELECT COUNT(*) FROM ReviewLikes WHERE review_id = ?
        ''', (review_id,)).fetchone()[0]

        conn.commit()
        return jsonify({
            'success': True,
            'is_liked': new_status,
            'like_count': like_count
        })

    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': f'Ошибка базы данных: {str(e)}'}), 500
    finally:
        conn.close()



@app.route('/rate_book', methods=['POST'])
def rate_book():
    if 'user_email' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401

    data = request.get_json()
    raw_isbn = data['isbn']

    # Нормализация ISBN
    clean_isbn = raw_isbn.strip()

    conn = get_db_connection()
    try:
        # Проверка существования книги
        book_exists = conn.execute('SELECT 1 FROM Books WHERE isbn = ?', (clean_isbn,)).fetchone()
        if not book_exists:
            return jsonify({'success': False, 'error': 'Книга не найдена'}), 404

        # Обновление рейтинга
        with conn:
            # UPSERT оценки
            conn.execute('''
                INSERT INTO Ratings (user_email, isbn, rating)
                VALUES (?, ?, ?)
                ON CONFLICT(user_email, isbn) 
                DO UPDATE SET rating = excluded.rating
            ''', (session['user_email'], clean_isbn, data['rating']))

            # Пересчет среднего
            avg_rating = conn.execute('''
                SELECT 
                    COALESCE(ROUND(AVG(rating), 1), 0) as avg_rating,
                    COUNT(*) as rating_count
                FROM Ratings 
                WHERE isbn = ?
            ''', (clean_isbn,)).fetchone()

            # Атомарное обновление Books
            conn.execute('''
                UPDATE Books SET
                    rating = ?,
                    rating_count = ?
                WHERE isbn = ?
            ''', (
                avg_rating['avg_rating'],
                avg_rating['rating_count'],
                clean_isbn
            ))

        return jsonify({
            'success': True,
            'new_rating': avg_rating['avg_rating'],
            'rating_count': avg_rating['rating_count']
        })

    except sqlite3.IntegrityError as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка целостности данных: {str(e)}'
        }), 400
    except Exception as e:
        app.logger.error(f'Ошибка оценки: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }), 500
    finally:
        conn.close()


@app.route('/update_reading_history', methods=['POST'])
def update_reading_history():
    if 'user_email' not in session:
        print("Ошибка: user_email отсутствует в сессии")
        return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401

    data = request.get_json()
    isbn = data.get('isbn')

    if not isbn:
        print("Ошибка: isbn не указан")
        return jsonify({'success': False, 'error': 'Не указан ISBN'}), 400

    conn = None
    try:
        conn = get_db_connection()

        # Проверяем, существует ли книга
        book = conn.execute('SELECT isbn FROM Books WHERE isbn = ?', (isbn,)).fetchone()
        if not book:
            print(f"Книга не найдена: {isbn}")
            return jsonify({'success': False, 'error': 'Книга не найдена'}), 404

        # Обновляем поле popular
        conn.execute('''
            UPDATE Books 
            SET popular = popular + 1
            WHERE isbn = ?
        ''', (isbn,))

        # Добавляем или обновляем запись в ReadingHistory
        conn.execute('''
            INSERT INTO ReadingHistory (email, isbn)
            VALUES (?, ?)
            ON CONFLICT(email, isbn) 
            DO UPDATE SET added_date = CURRENT_TIMESTAMP
        ''', (session['user_email'], isbn))

        conn.commit()
        print(f"Популярность увеличена для isbn={isbn}, добавлена/обновлена история чтения для email={session['user_email']}")
        return jsonify({'success': True})

    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/search')
def search_books():
    search_query = request.args.get('q', '').strip()
    if not search_query:
        return jsonify([])

    conn = get_db_connection()
    try:
        keywords = [k for k in re.split(r'\s+', search_query) if k]
        if not keywords:
            return jsonify([])

        conditions = []
        params = []

        for keyword in keywords:
            like_pattern = f'%{keyword}%'
            conditions.append('''
                (b.title LIKE ? COLLATE NOCASE OR
                a.last_name LIKE ? COLLATE NOCASE OR 
                a.first_name LIKE ? COLLATE NOCASE OR
                b.isbn LIKE ? COLLATE NOCASE OR
                b.description LIKE ? COLLATE NOCASE OR
                b.age_rating LIKE ? COLLATE NOCASE OR
                CAST(b.publication_year AS TEXT) LIKE ? COLLATE NOCASE OR
                CAST(b.rating AS REAL) LIKE ? COLLATE NOCASE OR
                g.name LIKE ? COLLATE NOCASE OR
                p.name LIKE ? COLLATE NOCASE)
            ''')
            params.extend([like_pattern] * 10)

        where_clause = 'WHERE ' + ' OR '.join(conditions) if conditions else ''

        query = f'''
            SELECT DISTINCT
                b.title,
                a.last_name || ' ' || a.first_name AS author_name,
                b.cover_image_url,
                b.rating,
                b.isbn,
                b.description,
                b.age_rating,
                b.publication_year,
                GROUP_CONCAT(DISTINCT g.name) AS genres,
                GROUP_CONCAT(DISTINCT p.name) AS publishers
            FROM Books b
            JOIN BookAuthors ba ON b.isbn = ba.isbn
            JOIN Authors a ON ba.author_id = a.author_id
            LEFT JOIN BookGenres bg ON b.isbn = bg.isbn
            LEFT JOIN Genres g ON bg.genre_id = g.genre_id
            LEFT JOIN BookPublishers bp ON b.isbn = bp.isbn
            LEFT JOIN Publishers p ON bp.publisher_id = p.publisher_id
            {where_clause}
            GROUP BY b.isbn
            ORDER BY b.rating DESC
            LIMIT 50
        '''

        books = conn.execute(query, params).fetchall()
        return jsonify([dict(book) for book in books])

    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        conn.close()


@app.route('/get_books_by_genre/<genre_name>')
def get_books_by_genre(genre_name):
    conn = get_db_connection()
    try:
        books = conn.execute('''
            SELECT DISTINCT
                b.cover_image_url,
                b.title,
                a.last_name || ' ' || SUBSTR(a.first_name, 1, 1) || '. ' || 
                COALESCE(SUBSTR(a.middle_name, 1, 1) || '.', '') AS author_name,
                b.rating,
                b.isbn
            FROM Books b
            JOIN BookAuthors ba ON b.isbn = ba.isbn
            JOIN Authors a ON ba.author_id = a.author_id
            JOIN BookGenres bg ON b.isbn = bg.isbn
            JOIN Genres g ON bg.genre_id = g.genre_id
            WHERE g.name = ?
            ORDER BY b.rating DESC
            LIMIT 50
        ''', (genre_name,)).fetchall()

        return jsonify([dict(book) for book in books])
    except Exception as e:
        return jsonify({'error': str(e)})
    finally:
        conn.close()


@app.route('/toggle_favorite/<isbn>', methods=['POST'])
def toggle_favorite(isbn):
    if 'user_email' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401

    try:
        conn = get_db_connection()
        email = session['user_email']

        # Проверяем существование записи
        existing = conn.execute('''
            SELECT 1 FROM UserFavorites 
            WHERE email = ? AND isbn = ?
        ''', (email, isbn)).fetchone()

        if existing:
            # Удаляем из избранного
            conn.execute('''
                DELETE FROM UserFavorites 
                WHERE email = ? AND isbn = ?
            ''', (email, isbn))
            new_status = False
        else:
            # Добавляем в избранное
            conn.execute('''
                INSERT INTO UserFavorites (email, isbn)
                VALUES (?, ?)
            ''', (email, isbn))
            new_status = True

        conn.commit()
        return jsonify({'success': True, 'status': new_status})

    except sqlite3.IntegrityError as e:
        return jsonify({'success': False, 'error': 'Ошибка целостности данных'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


## Обновление профиля
@app.route('/update_profile', methods=['POST'])
def update_profile():
    try:
        new_username = request.form['username']
        new_birth_date = request.form['birth_date']

        conn = get_db_connection()
        conn.execute('''
            UPDATE Users SET
            username = ?,
            birth_date = ?
            WHERE email = ?
        ''', (new_username, new_birth_date, session['user_email']))
        conn.commit()

        # Рассчитываем рейтинг на основе даты рождения
        birth_date = datetime.strptime(new_birth_date, '%Y-%m-%d').date()
        age = (datetime.now().date() - birth_date).days // 365
        allowed_rating = f"{age}+"

        return jsonify({
            'success': True,
            'username': new_username,
            'birth_date': new_birth_date,
            'allowed_rating': allowed_rating
        })

    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Имя занято'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'error': 'Файл не выбран'})

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Пустой файл'})

    try:
        filename = f"{session['user_email']}_{secure_filename(file.filename)}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        avatar_url = url_for('static', filename=f'uploads/avatars/{filename}')

        # Сохранение в БД
        conn = get_db_connection()
        conn.execute('''
            UPDATE Users SET avatar_url = ?
            WHERE email = ?
        ''', (avatar_url, session['user_email']))
        conn.commit()

        # Обновление сессии
        session['user_avatar'] = avatar_url

        return jsonify({
            'success': True,
            'avatar_url': avatar_url + '?t=' + str(time.time())
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        if 'conn' in locals():
            conn.close()


@app.route('/admin_statistics', methods=['GET'])
def admin_statistics():
    if 'user_email' not in session or session['user_role'] != 3:
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

    # Получаем параметр period (по умолчанию 12 месяцев)
    period = request.args.get('period', '12', type=int)
    if period not in [3, 6, 12]:
        period = 12

    conn = get_db_connection()
    try:
        # 1. Активность пользователей по месяцам
        activity_data = conn.execute('''
            SELECT 
                strftime('%Y-%m', added_date) AS month,
                COUNT(*) AS read_count
            FROM ReadingHistory
            WHERE added_date >= date('now', ? || ' months')
            GROUP BY month
            ORDER BY month
        ''', (f'-{period}',)).fetchall()
        activity_stats = {
            'labels': [row['month'] for row in activity_data],
            'data': [row['read_count'] for row in activity_data]
        }
        if not activity_data:
            activity_stats = {'labels': ['Нет данных'], 'data': [0]}

        # 2. Популярность жанров
        genre_data = conn.execute('''
            SELECT 
                g.name AS genre,
                COUNT(r.history_id) AS read_count
            FROM Genres g
            JOIN BookGenres bg ON g.genre_id = bg.genre_id
            JOIN Books b ON bg.isbn = b.isbn
            JOIN ReadingHistory r ON b.isbn = r.isbn
            WHERE r.added_date >= date('now', ? || ' months')
            GROUP BY g.genre_id, g.name
            ORDER BY read_count DESC
            LIMIT 8
        ''', (f'-{period}',)).fetchall()
        genre_stats = {
            'labels': [row['genre'] for row in genre_data],
            'data': [row['read_count'] for row in genre_data]
        }
        if not genre_data:
            genre_stats = {'labels': ['Нет данных'], 'data': [0]}

        # 3. Новые пользователи по месяцам
        new_users_data = conn.execute('''
            SELECT 
                strftime('%Y-%m', MIN(added_date)) AS month,
                COUNT(DISTINCT email) AS new_users
            FROM ReadingHistory
            WHERE added_date >= date('now', ? || ' months')
            GROUP BY strftime('%Y-%m', added_date)
            ORDER BY month
        ''', (f'-{period}',)).fetchall()
        new_users_stats = {
            'labels': [row['month'] for row in new_users_data],
            'data': [row['new_users'] for row in new_users_data]
        }
        if not new_users_data:
            new_users_stats = {'labels': ['Нет данных'], 'data': [0]}

        # 4. Статистика по возрастам читателей
        age_data = conn.execute('''
            SELECT 
                CASE 
                    WHEN (julianday('now') - julianday(birth_date)) / 365.25 < 13 THEN '0-12'
                    WHEN (julianday('now') - julianday(birth_date)) / 365.25 < 18 THEN '13-17'
                    WHEN (julianday('now') - julianday(birth_date)) / 365.25 < 30 THEN '18-29'
                    WHEN (julianday('now') - julianday(birth_date)) / 365.25 < 50 THEN '30-49'
                    ELSE '50+'
                END AS age_group,
                COUNT(DISTINCT u.email) as user_count
            FROM Users u
            JOIN ReadingHistory r ON u.email = r.email
            WHERE r.added_date >= date('now', ? || ' months')
                AND u.birth_date IS NOT NULL
            GROUP BY age_group
            ORDER BY age_group
        ''', (f'-{period}',)).fetchall()
        age_stats = {
            'labels': [row['age_group'] for row in age_data],
            'data': [row['user_count'] for row in age_data]
        }
        if not age_data:
            age_stats = {'labels': ['Нет данных'], 'data': [0]}

        # 5. Самые читаемые книги
        popular_books = conn.execute('''
            SELECT 
                b.title,
                COUNT(r.history_id) as read_count
            FROM Books b
            JOIN ReadingHistory r ON b.isbn = r.isbn
            WHERE r.added_date >= date('now', ? || ' months')
            GROUP BY b.isbn, b.title
            ORDER BY read_count DESC
            LIMIT 5
        ''', (f'-{period}',)).fetchall()
        books_stats = {
            'labels': [row['title'] for row in popular_books],
            'data': [row['read_count'] for row in popular_books]
        }
        if not popular_books:
            books_stats = {'labels': ['Нет данных'], 'data': [0]}

        return jsonify({
            'success': True,
            'activity_stats': activity_stats,
            'genre_stats': genre_stats,
            'new_users_stats': new_users_stats,
            'age_stats': age_stats,
            'books_stats': books_stats
        })

    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': f'Ошибка базы данных: {str(e)}'}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)