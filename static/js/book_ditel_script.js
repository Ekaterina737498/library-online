function showEditForm() {
    document.getElementById('editForm').style.display = 'block';
    document.querySelector('.book-details').style.display = 'none';
}

function cancelEdit() {
    document.getElementById('editForm').style.display = 'none';
    document.querySelector('.book-details').style.display = 'block';
}

function showDeleteConfirmation() {
    document.getElementById('deleteConfirmation').style.display = 'flex';
}

function cancelDelete() {
    document.getElementById('deleteConfirmation').style.display = 'none';
}

function saveBookChanges() {
    const form = document.getElementById('editBookForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    data.isbn = document.querySelector('[data-isbn]').dataset.isbn;

    fetch('/edit_book', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Книга успешно обновлена');
            location.reload();
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Ошибка соединения');
    });
}

function deleteBook() {
    const isbn = document.querySelector('[data-isbn]').dataset.isbn;

    fetch(`/delete_book/${isbn}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Книга успешно удалена');
            window.location.href = '/home';
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Ошибка соединения');
    });
}

function addReview() {
    const reviewInput = document.getElementById('reviewInput');
    const reviewText = reviewInput.value.trim();
    const isbn = document.querySelector('[data-isbn]').dataset.isbn;

    if (!reviewText) {
        alert('Пожалуйста, введите текст отзыва');
        return;
    }

    fetch('/add_review', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            isbn: isbn,
            content: reviewText
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.error || `HTTP ошибка: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const reviewsContainer = document.getElementById('reviewsContainer');
            const newReview = document.createElement('div');
            newReview.className = 'review parent-review';
            newReview.id = `review${data.review.review_id}`;
            newReview.setAttribute('data-email', data.review.email);
            newReview.setAttribute('data-isbn', isbn);

            const canDelete = data.current_user_email === data.review.email || data.current_user_role === 3;
            const deleteButton = canDelete
                ? `<button class="delete-review-button" onclick="deleteReview('${data.review.review_id}', '${isbn}')">Удалить</button>`
                : '';

            newReview.innerHTML = `
                <div class="review-header">
                    <img src="${data.review.avatar_url}" alt="Avatar" class="avatar">
                    <span class="username">${data.review.username}</span>
                    <span class="date">${new Date(data.review.created_date).toLocaleDateString('ru-RU')}</span>
                    <div class="review-actions">
                        <button class="like-button" onclick="toggleLike('${data.review.review_id}')" data-review-id="${data.review.review_id}">
                            👍 0
                        </button>
                        <button class="replies-toggle" onclick="toggleReplies('${data.review.review_id}')" data-review-id="${data.review.review_id}">
                            Отзывы (0)
                        </button>
                        ${deleteButton}
                    </div>
                </div>
                <div class="review-content">
                    <p>${data.review.content}</p>
                </div>
                <div class="reply-form" style="display: none;">
                    <textarea class="reply-input" placeholder="Напишите ваш ответ..."></textarea>
                    <button onclick="addReply('${data.review.review_id}', '${isbn}')">Отправить</button>
                </div>
                <div class="child-reviews" id="replies${data.review.review_id}" style="display: none;"></div>
            `;
            reviewsContainer.prepend(newReview);
            reviewInput.value = '';
            showToast('Отзыв успешно добавлен');
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert(`Ошибка: ${error.message}`);
    });
}

function addReply(parentReviewId, isbn) {
    const replyInput = document.querySelector(`#review${parentReviewId} .reply-input`);
    const replyText = replyInput.value.trim();

    if (!replyText) {
        alert('Пожалуйста, введите текст ответа');
        return;
    }

    fetch('/add_reply', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            isbn: isbn,
            content: replyText,
            parent_review_id: parentReviewId
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.error || `HTTP ошибка: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const repliesContainer = document.getElementById(`replies${parentReviewId}`);
            const newReply = document.createElement('div');
            newReply.className = 'review child-review';
            newReply.id = `review${data.review.review_id}`;
            newReply.setAttribute('data-email', data.review.email);
            newReply.setAttribute('data-isbn', isbn);

            const canDelete = data.current_user_email === data.review.email || data.current_user_role === 3;
            const deleteButton = canDelete
                ? `<button class="delete-review-button" onclick="deleteReview('${data.review.review_id}', '${isbn}')">Удалить</button>`
                : '';

            newReply.innerHTML = `
                <div class="review-header">
                    <img src="${data.review.avatar_url}" alt="Avatar" class="avatar">
                    <span class="username">${data.review.username}</span>
                    <span class="date">${new Date(data.review.created_date).toLocaleDateString('ru-RU')}</span>
                    <div class="review-actions">
                        <button class="like-button ${data.review.is_liked ? 'liked' : ''}"
                                onclick="toggleLike('${data.review.review_id}')"
                                data-review-id="${data.review.review_id}">
                            👍 ${data.review.like_count}
                        </button>
                        ${deleteButton}
                    </div>
                </div>
                <div class="review-content">
                    <p>${data.review.content}</p>
                </div>
            `;
            repliesContainer.appendChild(newReply);
            replyInput.value = '';

            // Обновляем счётчик ответов
            const toggleButton = document.querySelector(`button.replies-toggle[data-review-id="${parentReviewId}"]`);
            const currentCount = parseInt(toggleButton.textContent.match(/\d+/)[0]);
            toggleButton.textContent = `Отзывы (${currentCount + 1})`;

            showToast('Ответ успешно добавлен');
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert(`Ошибка: ${error.message}`);
    });
}

function toggleReplies(reviewId) {
    const repliesContainer = document.getElementById(`replies${reviewId}`);
    const replyForm = document.querySelector(`#review${reviewId} .reply-form`);
    const isVisible = repliesContainer.style.display === 'block';

    repliesContainer.style.display = isVisible ? 'none' : 'block';
    if (replyForm) {
        replyForm.style.display = isVisible ? 'none' : 'block';
    }
}

function toggleLike(reviewId) {
    fetch(`/toggle_review_like/${reviewId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.error || `HTTP ошибка: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const likeButton = document.querySelector(`.like-button[data-review-id="${reviewId}"]`);
            likeButton.classList.toggle('liked', data.is_liked);
            likeButton.innerHTML = `👍 ${data.like_count}`;
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert(`Ошибка: ${error.message}`);
    });
}

function showDeleteReviewConfirmation(reviewId, isbn) {
    const modal = document.createElement('div');
    modal.id = 'deleteReviewConfirmation';
    modal.innerHTML = `
        <div class="modal-content">
            <h2>Подтверждение удаления</h2>
            <p>Вы уверены, что хотите удалить этот отзыв?</p>
            <button onclick="confirmDeleteReview('${reviewId}', '${isbn}')">Удалить</button>
            <button onclick="cancelDeleteReview()">Отменить</button>
        </div>
    `;
    document.body.appendChild(modal);
}

function confirmDeleteReview(reviewId, isbn) {
    fetch(`/delete_review/${reviewId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ isbn: isbn })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.error || `HTTP ошибка: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const reviewElement = document.getElementById(`review${reviewId}`);
            if (reviewElement) {
                reviewElement.style.opacity = '0';
                setTimeout(() => reviewElement.remove(), 300);
            }
            cancelDeleteReview();
            showToast('Отзыв успешно удален');
        } else {
            alert('Ошибка: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Ошибка при удалении отзыва:', error);
        alert(`Ошибка: ${error.message}`);
    });
}

function cancelDeleteReview() {
    const modal = document.getElementById('deleteReviewConfirmation');
    if (modal) {
        modal.remove();
    }
}

function deleteReview(reviewId, isbn) {
    showDeleteReviewConfirmation(reviewId, isbn);
}

function setRating(rating) {
    const stars = document.querySelectorAll('.star');
    stars.forEach((star, index) => {
        star.classList.toggle('selected', index < rating);
    });
    const isbn = document.querySelector('[data-isbn]').dataset.isbn;

    fetch('/rate_book', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            isbn: isbn,
            rating: rating
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('ratingCount').textContent =
                `Рейтинг: ${data.new_rating.toFixed(1)} (${data.rating_count} оценок)`;
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
    });
}

function toggleFavorite(isbn) {
    fetch(`/toggle_favorite/${isbn}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Ошибка сети');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const button = document.querySelector('.favorite-button');
            button.classList.toggle('active', data.status);
            button.innerHTML = data.status ? '❤️' : '🖤';
        }
    })
    .catch(error => console.error('Ошибка:', error));
}

function handleReadButtonClick(isbn, bookUrl) {
    const btn = document.querySelector('.read-button');
    const ageRating = parseInt(btn.dataset.ageRating) || 0;
    const allowedRating = parseInt(btn.dataset.allowedRating) || 0;

    if (ageRating > allowedRating) {
        showToast('Вы слишком молоды для этой книги!');
        return;
    }

    btn.disabled = true;

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
            const newWindow = window.open(bookUrl, '_blank');
            if (!newWindow || newWindow.closed) {
                window.location.href = bookUrl;
            }
        } else {
            showToast('Ошибка обновления истории: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast(error.message || 'Ошибка соединения');
    })
    .finally(() => {
        btn.disabled = false;
    });
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
