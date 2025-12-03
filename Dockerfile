# 使用官方 Python 映像檔作為基礎
FROM python:3.10-slim

# 安裝 git
RUN apt-get update && apt-get install -y git

# 設定工作目錄
WORKDIR /app

# 將 requirements.txt 複製到工作目錄並安裝相依套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 將專案中的所有檔案複製到工作目錄
COPY . .

# 設定預設執行的指令
CMD ["python", "run_all_v3.py"]
