// функции переключения вкладок
function showTab(tabName) {
    try {
        // Скрыть все вкладки содержимого
        document.querySelectorAll('.content > .tab').forEach(tab => {
            tab.style.display = 'none';
        });

        // Показать выбранную вкладку
        const targetTab = document.getElementById(tabName);
        if (!targetTab) {
            console.error(`Вкладка ${tabName} не найдена`);
            return;
        }

        // Обновить активное состояние кнопок
        document.querySelectorAll('.tab-header').forEach(header => {
            header.classList.remove('active');
        });
        document.querySelector(`.tab-header[onclick*="${tabName}"]`).classList.add('active');

        // Анимация появления
        targetTab.style.opacity = '0';
        targetTab.style.display = 'block';
        setTimeout(() => {
            targetTab.style.opacity = '1';
        }, 50);
    } catch (error) {
        console.error('Ошибка переключения вкладок:', error);
    }
}

// Показать/скрыть форму добавления книги
function toggleAddBookForm() {
    const form = document.getElementById('add-book-form');
    const button = document.getElementById('add-book-btn');
    if (form.style.display === 'none') {
        form.style.display = 'block';
        button.textContent = 'Скрыть форму';
    } else {
        form.style.display = 'none';
        button.textContent = 'Добавить книгу';
        document.getElementById('book-form').reset();
    }
}

// Отправка формы добавления книги
async function submitBook(event) {
    event.preventDefault();
    const form = document.getElementById('book-form');
    const formData = new FormData(form);
    const submitBtn = form.querySelector('.save-btn');

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Сохранение...';

        const response = await fetch('/add_book', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        const result = await response.json();
        if (result.success) {
            showToast('Книга успешно добавлена!', 'success');
            toggleAddBookForm(); // Скрыть форму и очистить
            form.reset();
        } else {
            throw new Error(result.error || 'Неизвестная ошибка');
        }
    } catch (error) {
        console.error('Ошибка добавления книги:', error);
        showToast(error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Сохранить';
    }
}


// Предпросмотр обложки по URL
function previewCoverImage() {
    const input = document.getElementById('cover_image_url');
    const preview = document.createElement('img');
    preview.id = 'cover-preview';
    preview.style.maxWidth = '100px';
    preview.style.marginTop = '10px';
    input.parentNode.appendChild(preview);

    input.addEventListener('input', () => {
        if (input.value) {
            preview.src = input.value;
            preview.onerror = () => {
                preview.src = '/static/default-book-cover.png';
                showToast('Неверный URL обложки', 'warning');
            };
        } else {
            preview.src = '/static/default-book-cover.png';
        }
    });
}

// Инициализация предпросмотра при загрузке
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('cover_image_url')) {
        previewCoverImage();
    }
});


async function updateProfile() {
    const response = await fetch('/update_profile', {
        method: 'POST',
        body: new URLSearchParams(new FormData(document.getElementById('profile-form'))),
        credentials: 'include'
    });

    const result = await response.json();
    if (result.success) {
        // Обновляем отображение профиля
        document.querySelector('input[name="username"]').value = result.username;
        document.querySelector('input[name="birth_date"]').value = result.birth_date;

        // Обновляем рейтинг
        const ratingBadge = document.querySelector('.rating-badge');
        ratingBadge.setAttribute('data-rating', result.allowed_rating);
    } else {
        showToast(result.error, 'error');
    }
}



// поиск книг
async function searchBooks() {
    const searchInput = document.getElementById('searchInput');
    const searchTerm = searchInput.value.trim();

    // Скрываем все стандартные полки
    document.querySelectorAll('.book-shelf').forEach(shelf => {
        shelf.style.display = 'none';
    });

    // Показываем полку результатов
    const resultsShelf = document.getElementById('search-results-shelf');
    resultsShelf.style.display = 'block';

    try {
        const response = await fetch(`/search?q=${encodeURIComponent(searchTerm)}`);
        const results = await response.json();

        const container = document.getElementById('search-results-container');
        container.innerHTML = '';

        if (results.error) {
            container.innerHTML = `<p class="error">${results.error}</p>`;
            return;
        }

        if (!results.length) {
            container.innerHTML = `
                <div class="no-results">
                    <p>По запросу "${searchTerm}" ничего не найдено</p>
                </div>`;
            return;
        }

        results.forEach(book => {
            const element = document.createElement('div');
            element.className = 'book-item';

            const formattedRating = parseFloat(book.rating).toFixed(1);

            element.innerHTML = `
                <img src="${book.cover_image_url}" alt="${book.title}">
                <div class="book-info">
                    <h4>${book.title}</h4>
                    <p>${book.author_name}</p>
                    <div class="rating">
                        ${'★'.repeat(Math.floor(book.rating))}
                        <span class="numeric-rating">${formattedRating}</span>
                    </div>
                </div>`;

            element.onclick = () => window.location.href = `/book/${book.isbn}`;
            container.appendChild(element);
        });


    } catch (error) {
        console.error('Search error:', error);
        showToast('Ошибка поиска', 'error');
    }
}

// Добавляем обработчик Enter
document.querySelector('.search-container input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') searchBooks();
});


function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    const cancelButton = document.getElementById('cancelSearch');
    const searchResults = document.getElementById('search-results-shelf');
    const originalShelves = document.querySelectorAll('.book-shelf:not(#search-results-shelf):not(#genre-results-shelf)');

    searchInput.addEventListener('input', function(e) {
        cancelButton.classList.toggle('visible', e.target.value.length > 0);
    });

    cancelButton.addEventListener('click', () => {
        searchInput.value = '';
        searchResults.style.display = 'none';
        originalShelves.forEach(shelf => shelf.style.display = 'block');
        cancelButton.classList.remove('visible');

        if (window.currentSearchRequest) {
            window.currentSearchRequest.abort();
        }
    });
}

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', setupSearch);


async function showGenre(genreName) {
    try {
        const response = await fetch(`/get_books_by_genre/${encodeURIComponent(genreName)}`);
        const books = await response.json();

        const container = document.getElementById('genre-results-container');
        const shelf = document.getElementById('genre-results-shelf');
        const title = shelf.querySelector('h3');


        // Очистка предыдущих результатов
        container.innerHTML = '';
        title.textContent = genreName;

        // Заполнение новыми данными
        books.forEach(book => {
            const bookElement = document.createElement('div');
            bookElement.className = 'book-item';
            // Форматирование с фиксированной десятичной точкой
            const formattedRating = parseFloat(book.rating).toFixed(1);
            bookElement.innerHTML = `
                <img src="${book.cover_image_url}" alt="${book.title}">
                <div class="book-info">
                    <h4>${book.title}</h4>
                    <p>${book.author_name}</p>
                    <div class="rating">
                        ${'★'.repeat(Math.floor(book.rating))}
                        <span class="numeric-rating">${formattedRating}</span>
                    </div>
                </div>
            `;
            bookElement.onclick = () => window.location.href = `/book/${book.isbn}`;
            container.appendChild(bookElement);
        });

        // Показываем результаты
        shelf.style.display = 'block';
        document.getElementById('cancelGener').classList.remove('hidden');

        // Скрываем другие полки
        document.querySelectorAll('.book-shelf:not(#genre-results-shelf)').forEach(s => {
            s.style.display = 'none';
        });
    } catch (error) {
        console.error('Ошибка загрузки жанра:', error);
        showToast('Ошибка загрузки книг', 'error');
    }
}

function clearGenre() {
    // Скрываем обе полки с результатами
    document.getElementById('genre-results-shelf').style.display = 'none';
    document.getElementById('search-results-shelf').style.display = 'none';

    // Сбрасываем поисковый запрос
    const searchInput = document.getElementById('searchInput');
    if (searchInput) searchInput.value = '';

    // Показываем основные полки
    document.querySelectorAll('.book-shelf:not(#genre-results-shelf):not(#search-results-shelf)').forEach(shelf => {
        shelf.style.display = 'block';
    });

    // Скрываем кнопку очистки
    document.getElementById('cancelGener').classList.add('hidden');
}



// функция загрузки аватара
function previewAvatar(event) {
    try {
        const file = event.target.files[0];
        if (!file || !file.type.startsWith('image/')) {
            showToast('Выберите изображение', 'warning');
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            document.querySelectorAll('.avatar, .editable-avatar').forEach(img => {
                img.style.opacity = 0;
                setTimeout(() => {
                    img.src = e.target.result;
                    img.style.opacity = 1;
                }, 200);
            });
        }
        reader.readAsDataURL(file);
    } catch (error) {
        console.error('Ошибка загрузки аватара:', error);
        showToast('Ошибка загрузки', 'error');
    }
}



function toggleEdit() {
    try {
        const form = document.getElementById('profile-form');
        if (!form) return;

        const saveBtn = form.querySelector('.save-btn');
        const editBtn = document.getElementById('edit-btn');

        // Переключение режима редактирования
        const inputs = form.querySelectorAll('input[readonly]');
        inputs.forEach(input => {
            input.readOnly = !input.readOnly;
            input.style.border = input.readOnly ? 'none' : '2px solid #6b8dd6';
        });

        // Обновление кнопок
        saveBtn.hidden = !saveBtn.hidden;
        editBtn.hidden = saveBtn.hidden;

        // Добавляем обработчик отправки формы
        form.onsubmit = submitProfile;
    } catch (error) {
        console.error('Ошибка редактирования:', error);
        showToast('Ошибка редактирования профиля', 'error');
    }
}

// обработчик загрузки аватара
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('home').style.display = 'block';
    showTab('home');
    document.getElementById('profile-form').addEventListener('submit', submitProfile);
    const avatarUpload = document.getElementById('avatar-upload');
    const ratingBadge = document.querySelector('.rating-badge');
    const initialRating = ratingBadge.dataset.rating || '0';
    ratingBadge.textContent = initialRating;
    document.querySelector('.logout-btn').addEventListener('click', function(e) {
        e.preventDefault();
        logout();
    });

    if (!avatarUpload) return;

    avatarUpload.addEventListener('change', function(e) {
        try {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function(event) {
                document.querySelectorAll('.avatar, .editable-avatar').forEach(img => {
                    if (img instanceof HTMLImageElement) {
                        img.src = event.target.result;
                    }
                });
            };
            reader.readAsDataURL(file);
        } catch (error) {
            console.error('Ошибка загрузки аватара:', error);
            alert('Ошибка при загрузке изображения');
        }
    });
});

// функция выхода
async function logout() {
    try {
        const response = await fetch('/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });

        // Проверка редиректа
        if (response.redirected) {
            window.location.href = response.url;
            return;
        }

        // Обработка JSON-ответа
        const result = await response.json();
        if (result.redirect) {
            window.location.href = result.redirect;
        } else {
            throw new Error('Ошибка сервера');
        }
    } catch (error) {
        console.error('Ошибка выхода:', error);
        showToast(`Ошибка: ${error.message}`, 'error');
        // Принудительный редирект
        setTimeout(() => window.location.href = '/index', 2000);
    }
}

// функция для обновления интерфейса
function updateUI(data) {

    // Обновление никнейма
    document.querySelectorAll('.nickname').forEach(el => {
        el.textContent = data.username;
    });
    // Обновление даты рождения
    document.querySelector('input[name="birth_date"]').value = data.birth_date;

    // Обновление рейтинга с проверкой источника данных
    const ratingValue = data.allowed_rating ||
                      document.querySelector('.rating-badge').dataset.rating ||
                      '0';

    document.querySelector('.rating-badge').textContent = ratingValue;
    document.querySelector('.rating-badge').dataset.rating = ratingValue;

    // Анимация обновления
    document.querySelectorAll('input, .rating-badge').forEach(el => {
        el.classList.add('updated-field');
        setTimeout(() => el.classList.remove('updated-field'), 1500);
    });
}

// Дополнительная функция для обновления рейтинга
function refreshRating() {
    fetch('/get_rating')
        .then(response => response.json())
        .then(data => {
            document.querySelector('.rating-badge').textContent = data.rating;
            document.querySelector('.rating-badge').dataset.rating = data.rating;
        });
}

// отправка профиля
async function submitProfile(e) {
    e.preventDefault();
    const activeTab = document.querySelector('.tab-header.active').getAttribute('onclick').replace("showTab('", "").replace("')", ""); // Получаем активную вкладку

    const form = document.getElementById('profile-form');
    const formData = new FormData(form);

    // Удаляем аватар из данных если не выбран новый файл
    if (!document.getElementById('avatarInput').files.length) {
        formData.delete('avatar'); // Убираем поле если файл не выбран
        formData.append('keep_avatar', 'true'); // Добавляем флаг для сервера
    }

    const submitBtn = form.querySelector('button[type="submit"]');
    try {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Сохранение...';

        const response = await fetch('/update_profile', {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });

        if (!response.ok) throw new Error('Ошибка сервера');

        const result = await response.json();
        if (result.success) {
            // Обновление данных на странице
            updateUI(result); // Обновляем интерфейс
            updateProfile(); // Обновляем рейтинг
            toggleEdit(); // Возврат в режим просмотра
            document.querySelector('.save-btn').style.display = 'none'; // Скрытие кнопки "Сохранить"
            showTab(activeTab); // Возврат на текущую вкладку
            showToast('Изменения сохранены!', 'success');
        } else {
            throw new Error(result.error || 'Неизвестная ошибка');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showToast(error.message, 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Сохранить';
    }
}

// Вспомогательная функция уведомлений
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}


// Инициализация слайдеров
document.querySelectorAll('.shelf').forEach(shelf => {
    let isDown = false;
    let startX;
    let scrollLeft;

    shelf.addEventListener('mousedown', (e) => {
        isDown = true;
        startX = e.pageX - shelf.offsetLeft;
        scrollLeft = shelf.scrollLeft;
    });

    shelf.addEventListener('mouseleave', () => {
        isDown = false;
    });

    shelf.addEventListener('mouseup', () => {
        isDown = false;
    });

    shelf.addEventListener('mousemove', (e) => {
        if (!isDown) return;
        e.preventDefault();
        const x = e.pageX - shelf.offsetLeft;
        const walk = (x - startX) * 2;
        shelf.scrollLeft = scrollLeft - walk;
    });
});

// Кнопки управления слайдером
document.querySelectorAll('.shelf').forEach(shelf => {
    const controls = document.createElement('div');
    controls.className = 'shelf-controls';

    const prevButton = document.createElement('button');
    prevButton.className = 'slider-btn';
    prevButton.textContent = '←';
    prevButton.onclick = () => {
        shelf.scrollBy({ left: -430, behavior: 'smooth' });
    };

    const nextButton = document.createElement('button');
    nextButton.className = 'slider-btn';
    nextButton.textContent = '→';
    nextButton.onclick = () => {
        shelf.scrollBy({ left: 430, behavior: 'smooth' });
    };

    controls.appendChild(prevButton);
    controls.appendChild(nextButton);
    shelf.parentNode.insertBefore(controls, shelf.nextSibling);
});


// Хранилище объектов Chart.js и текущих параметров скачивания
const charts = {};
let currentChartId = null;
let currentFilename = null;

// Загрузка статистики
function loadAdminStatistics(period = 12) {
    fetch(`/admin_statistics?period=${period}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Уничтожаем существующие диаграммы, если они есть
            Object.values(charts).forEach(chart => chart && chart.destroy());
            charts.activityChart = null;
            charts.genreChart = null;
            charts.newUsersChart = null;
            charts.ageChart = null;
            charts.popularBooksChart = null;

            // 1. Активность пользователей
            const activityCtx = document.getElementById('activityChart').getContext('2d');
            charts.activityChart = new Chart(activityCtx, {
                type: 'line',
                data: {
                    labels: data.activity_stats.labels,
                    datasets: [{
                        label: 'Количество прочтений',
                        data: data.activity_stats.data,
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: 'Прочтения' }
                        },
                        x: {
                            title: { display: true, text: 'Месяц' }
                        }
                    }
                }
            });

            // 2. Популярность жанров
            const genreCtx = document.getElementById('genreChart').getContext('2d');
            charts.genreChart = new Chart(genreCtx, {
                type: 'pie',
                data: {
                    labels: data.genre_stats.labels,
                    datasets: [{
                        label: 'Прочтения по жанрам',
                        data: data.genre_stats.data,
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.2)',
                            'rgba(54, 162, 235, 0.2)',
                            'rgba(255, 206, 86, 0.2)',
                            'rgba(75, 192, 192, 0.2)',
                            'rgba(153, 102, 255, 0.2)',
                            'rgba(255, 159, 64, 0.2)',
                            'rgba(199, 199, 199, 0.2)',
                            'rgba(83, 102, 255, 0.2)'
                        ],
                        borderColor: [
                            'rgba(255, 99, 132, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(153, 102, 255, 1)',
                            'rgba(255, 159, 64, 1)',
                            'rgba(199, 199, 199, 1)',
                            'rgba(83, 102, 255, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    plugins: {
                        legend: {
                            position: 'right'
                        }
                    }
                }
            });

            // 3. Новые пользователи
            const newUsersCtx = document.getElementById('newUsersChart').getContext('2d');
            charts.newUsersChart = new Chart(newUsersCtx, {
                type: 'bar',
                data: {
                    labels: data.new_users_stats.labels,
                    datasets: [{
                        label: 'Новые пользователи',
                        data: data.new_users_stats.data,
                        backgroundColor: 'rgba(255, 159, 64, 0.2)',
                        borderColor: 'rgba(255, 159, 64, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: 'Количество' }
                        },
                        x: {
                            title: { display: true, text: 'Месяц' }
                        }
                    }
                }
            });

            // 4. Статистика по возрастам
            const ageCtx = document.getElementById('ageChart').getContext('2d');
            charts.ageChart = new Chart(ageCtx, {
                type: 'bar',
                data: {
                    labels: data.age_stats.labels,
                    datasets: [{
                        label: 'Количество читателей',
                        data: data.age_stats.data,
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: 'Количество' }
                        },
                        x: {
                            title: { display: true, text: 'Возрастная группа' }
                        }
                    }
                }
            });

            // 5. Самые читаемые книги
            const booksCtx = document.getElementById('popularBooksChart').getContext('2d');
            charts.popularBooksChart = new Chart(booksCtx, {
                type: 'bar',
                data: {
                    labels: data.books_stats.labels,
                    datasets: [{
                        label: 'Количество прочтений',
                        data: data.books_stats.data,
                        backgroundColor: 'rgba(153, 102, 255, 0.2)',
                        borderColor: 'rgba(153, 102, 255, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: 'Прочтения' }
                        },
                        x: {
                            title: { display: true, text: 'Название книги' }
                        }
                    }
                }
            });
        } else {
            showToast(data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Ошибка загрузки статистики:', error);
        showToast('Ошибка загрузки статистики', 'error');
    });
}

// Обновление статистики при смене фильтра
function updateStatistics() {
    const period = document.getElementById('periodFilter').value;
    loadAdminStatistics(period);
}

// Открытие модального окна для выбора формата
function openDownloadModal(chartId, filename) {
    currentChartId = chartId;
    currentFilename = filename;
    const modal = document.getElementById('downloadModal');
    modal.style.display = 'flex';
}

// Закрытие модального окна
function closeDownloadModal() {
    const modal = document.getElementById('downloadModal');
    modal.style.display = 'none';
    currentChartId = null;
    currentFilename = null;
}

// Скачивание диаграммы в выбранном формате
function downloadSelectedChart(format) {
    if (!currentChartId || !currentFilename) {
        showToast('Диаграмма не выбрана', 'error');
        closeDownloadModal();
        return;
    }

    const canvas = document.getElementById(currentChartId);
    if (!canvas) {
        showToast('Диаграмма не найдена', 'error');
        closeDownloadModal();
        return;
    }

    try {
        if (format === 'png') {
            // Скачивание как PNG
            const link = document.createElement('a');
            link.href = canvas.toDataURL('image/png');
            link.download = `${currentFilename}.png`;
            link.click();
            showToast('Диаграмма успешно скачана как PNG', 'success');
        } else if (format === 'pdf') {
            // Скачивание как PDF (только диаграмма)
            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF({
                orientation: 'portrait',
                unit: 'mm',
                format: 'a4'
            });

            // Добавляем диаграмму
            const imgData = canvas.toDataURL('image/png');
            pdf.addImage(imgData, 'PNG', 10, 10, 180, 90);

            // Сохраняем PDF
            pdf.save(`${currentFilename}.pdf`);
            showToast('Диаграмма успешно скачана как PDF', 'success');
        }
    } catch (error) {
        console.error(`Ошибка скачивания (${format}):`, error);
        showToast(`Ошибка при скачивании в формате ${format.toUpperCase()}`, 'error');
    }

    closeDownloadModal();
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Загрузка статистики при открытии вкладки Админ
    const adminTab = document.querySelector('.tab-header[onclick="showTab(\'admin\')"]');
    if (adminTab) {
        adminTab.addEventListener('click', () => {
            loadAdminStatistics();
        });
    }

    // Закрытие модального окна при клике вне контента
    const modal = document.getElementById('downloadModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeDownloadModal();
            }
        });
    }

    // Инициализация статистики с фильтром по умолчанию
    if (document.getElementById('periodFilter')) {
        loadAdminStatistics();
    }
});

// Управление сворачиванием верхней панели
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.querySelector('.sidebar');
    const headerUser = document.querySelector('.header-user');

    // Проверяем ширину экрана при загрузке
    if (window.innerWidth <= 768) {
        sidebar.classList.add('collapsed');
    }

    // Переключение сворачивания по клику на аватарку
    headerUser.addEventListener('click', (e) => {
        e.stopPropagation();
        sidebar.classList.toggle('collapsed');
    });

    // Закрытие панели при клике вне
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 && !sidebar.contains(e.target) && !sidebar.classList.contains('collapsed')) {
            sidebar.classList.add('collapsed');
        }
    });

    // Обновление при ресайзе
    window.addEventListener('resize', () => {
        if (window.innerWidth <= 768) {
            sidebar.classList.add('collapsed');
        } else {
            sidebar.classList.remove('collapsed');
        }
    });
});


function handleReadButtonClick(isbn, filePath) {
    // Блокировка кнопки на время обработки
    const btn = document.querySelector('.read-button');
    btn.disabled = true;

    // Обновление истории чтения
    fetch('/update_reading_history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isbn: isbn })
    })
    .then(response => {
        if (!response.ok) throw new Error('Ошибка сети');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Открытие книги после успешного обновления
            const bookUrl = `/static/${filePath}`;
            const newWindow = window.open(bookUrl, '_blank');

            // Резервное открытие если браузер блокирует popup
            if (!newWindow || newWindow.closed) {
                window.location.href = bookUrl;
            }
        } else {
            alert('Ошибка обновления истории: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert(error.message || 'Ошибка соединения');
    })
    .finally(() => {
        btn.disabled = false;
    });
}
