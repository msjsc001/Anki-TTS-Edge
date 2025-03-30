# 使用完整版Python镜像包含tkinter依赖
FROM python:3.10

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y \
    python3-tk \
    tk-dev \
    libtk8.6 \
    xclip \
    xsel \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install pynput pyperclip pygobject

# 暴露端口
EXPOSE 8000

# 设置启动命令
CMD ["python", "Anki-TTS-Edge.py"]