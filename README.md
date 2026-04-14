# 1. Скопировать репозиторий
git clone https://github.com/JustUty/VSM.git

# 2. Зайти в папку
cd VSM

# 3. Создать виртуальное окружение
python -m venv venv

# 4. Активировать его
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 5. Установить зависимости
pip install -r requirements.txt

# 6. Запустить приложение
streamlit run app.py