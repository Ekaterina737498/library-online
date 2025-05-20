// Обработчик выбора файла
document.getElementById('avatarInput').addEventListener('change', async function(e) {
    const file = e.target.files[0];

    if (file) {
        const reader = new FileReader();
        reader.onload = async function(event) {
            // Обновление превью
            document.querySelectorAll('#previewAvatar, #sidebarAvatar').forEach(img => {
                img.src = event.target.result;
            });

            // Автоматическое сохранение
            await saveAvatar(file); // Передаем файл для сохранения
        };
        reader.readAsDataURL(file);
    }
});

function handleAvatarUpload(event) {
    const file = event.target.files[0];

    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            // Обновление превью
            document.getElementById('previewAvatar').src = e.target.result;
        };
        reader.readAsDataURL(file);

        // Автоматическое сохранение
        saveAvatar(file); // Передаем файл для сохранения
    }
}

// Асинхронное сохранение
async function saveAvatar(file) {
    const formData = new FormData();
    formData.append('avatar', file);

    try {
        const response = await fetch('/upload_avatar', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        const result = await response.json();
        if (result.success) {
            document.querySelectorAll('.avatar').forEach(img => {
                img.src = result.avatar_url;
            });
            showToast('Аватар успешно сохранен!', 'success');
        } else {
            showToast(result.error, 'error');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showToast('Ошибка при сохранении аватара', 'error');
    }
}


// Вспомогательная функция уведомлений
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}