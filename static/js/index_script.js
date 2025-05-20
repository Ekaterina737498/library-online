function showTab(tabName) {
            const tabs = document.querySelectorAll('.tab');
            const headers = document.querySelectorAll('.tab-header');
            tabs.forEach(tab => {
                tab.style.display = 'none';
            });
            headers.forEach(header => {
                header.classList.remove('active');
            });
            document.getElementById(tabName).style.display = 'block';
            document.querySelector(`.tab-header[onclick="showTab('${tabName}')"]`).classList.add('active');
        }

