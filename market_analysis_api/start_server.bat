@echo off
echo Starting Django development server...
echo.
echo Make sure you have:
echo 1. Created a virtual environment
echo 2. Installed dependencies: pip install -r requirements.txt
echo 3. Run migrations: python manage.py migrate
echo.
python manage.py runserver 8003

