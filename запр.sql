-- Таблица авторов
CREATE TABLE Authors (
    author_id INTEGER PRIMARY KEY AUTOINCREMENT,
    last_name VARCHAR(50) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    middle_name VARCHAR(50) NOT NULL
);

-- Таблица книг
CREATE TABLE Books (
    isbn VARCHAR(20) UNIQUE PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    publication_year INTEGER,
    cover_image_url TEXT,
    age_rating VARCHAR(10),
    total_pages INTEGER NOT NULL DEFAULT 1 CHECK(total_pages > 0),
    popular INTEGER DEFAULT 0,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rating_count INTEGER DEFAULT 0,
    rating REAL DEFAULT 0
);

-- Таблица жанров
CREATE TABLE Genres (
    genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL
);

-- Таблица издателей
CREATE TABLE Publishers (
    publisher_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL
);

-- Таблица связи книг и авторов
CREATE TABLE BookAuthors (
    isbn VARCHAR(20) NOT NULL,
    author_id INTEGER NOT NULL,
    PRIMARY KEY (isbn, author_id),
    FOREIGN KEY (isbn) REFERENCES Books(isbn) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES Authors(author_id) ON DELETE CASCADE
);

-- Таблица файлов книг
CREATE TABLE BookFiles (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn VARCHAR(20) NOT NULL,
    file_path TEXT NOT NULL,
    FOREIGN KEY (isbn) REFERENCES Books(isbn) ON DELETE CASCADE
);

-- Таблица связи книг и жанров
CREATE TABLE BookGenres (
    isbn VARCHAR(20) NOT NULL,
    genre_id INTEGER NOT NULL,
    PRIMARY KEY (isbn, genre_id),
    FOREIGN KEY (isbn) REFERENCES Books(isbn) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES Genres(genre_id) ON DELETE CASCADE
);

-- Таблица связи книг и издателей
CREATE TABLE BookPublishers (
    isbn VARCHAR(20) NOT NULL,
    publisher_id INTEGER NOT NULL,
    PRIMARY KEY (isbn, publisher_id),
    FOREIGN KEY (isbn) REFERENCES Books(isbn) ON DELETE CASCADE,
    FOREIGN KEY (publisher_id) REFERENCES Publishers(publisher_id) ON DELETE CASCADE
);

-- Таблица пользователей
CREATE TABLE Users (
    email VARCHAR(100) NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    birth_date DATE,
    avatar_url TEXT DEFAULT '/static/default_avatar.png',
    PRIMARY KEY (email)
);

-- Таблица ролей пользователей
CREATE TABLE UserRoles (
    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name VARCHAR(50) UNIQUE NOT NULL
);

-- Таблица назначения ролей пользователям
CREATE TABLE UserRoleAssignments (
    email VARCHAR(100) NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (email, role_id),
    FOREIGN KEY (email) REFERENCES Users(email) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES UserRoles(role_id) ON DELETE CASCADE
);

-- Таблица оценок
CREATE TABLE Ratings (
    user_email VARCHAR(255) NOT NULL,
    isbn VARCHAR(20) NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_email, isbn),
    FOREIGN KEY (user_email) REFERENCES Users(email) ON DELETE CASCADE,
    FOREIGN KEY (isbn) REFERENCES Books(isbn) ON DELETE CASCADE
);

-- Таблица истории чтения
CREATE TABLE ReadingHistory (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(100) NOT NULL,
    isbn VARCHAR(20) NOT NULL,
    added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(email, isbn),
    FOREIGN KEY (email) REFERENCES Users(email) ON DELETE CASCADE,
    FOREIGN KEY (isbn) REFERENCES Books(isbn) ON DELETE CASCADE
);

-- Таблица отзывов
CREATE TABLE Reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(100) NOT NULL,
    isbn VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parent_review_id INTEGER,
    FOREIGN KEY (email) REFERENCES Users(email) ON DELETE CASCADE,
    FOREIGN KEY (isbn) REFERENCES Books(isbn) ON DELETE CASCADE,
    FOREIGN KEY (parent_review_id) REFERENCES Reviews(review_id) ON DELETE CASCADE
);

-- Таблица лайков отзывов
CREATE TABLE ReviewLikes (
    email VARCHAR(100) NOT NULL,
    review_id INTEGER NOT NULL,
    PRIMARY KEY (email, review_id),
    FOREIGN KEY (email) REFERENCES Users(email) ON DELETE CASCADE,
    FOREIGN KEY (review_id) REFERENCES Reviews(review_id) ON DELETE CASCADE
);

-- Таблица избранных книг пользователей
CREATE TABLE UserFavorites (
    email VARCHAR(100) NOT NULL,
    isbn VARCHAR(20) NOT NULL,
    PRIMARY KEY (email, isbn),
    FOREIGN KEY (isbn) REFERENCES Books(isbn) ON DELETE CASCADE,
    FOREIGN KEY (email) REFERENCES Users(email) ON DELETE CASCADE
);

-- Индексы для оптимизации
CREATE INDEX idx_books_isbn ON Books(isbn);
CREATE INDEX idx_authors_id ON Authors(author_id);
CREATE INDEX idx_users_email ON Users(email);
CREATE INDEX idx_reviews_email ON Reviews(email);
CREATE INDEX idx_ratings_email ON Ratings(user_email);
CREATE INDEX idx_reading_history_email ON ReadingHistory(email);
