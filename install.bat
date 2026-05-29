@echo off
echo ================================
echo AA Email Cleaner Suite Setup
echo ================================

python -m venv venv

call venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt

echo Setup complete!
pause