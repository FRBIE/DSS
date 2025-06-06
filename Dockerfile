# 使用官方 Python 3.12 镜像
FROM python:3.12

# 设置工作目录
WORKDIR /app

# 添加日志
RUN echo "Starting Docker build process..."

# 配置pip使用清华源
RUN echo "Configuring pip to use Tsinghua mirror..."
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn && \
    echo "Pip configured to use Tsinghua mirror successfully"

# 复制 README.md
RUN echo "Copying README.md..."
COPY README.md /app/README.md
RUN echo "README.md copied successfully"

# 复制 Django 项目代码
RUN echo "Copying project files..."
COPY . .
RUN echo "Project files copied successfully"

# 安装 Poetry
RUN echo "Installing Poetry..."
RUN pip install poetry && echo "Poetry installed successfully"

# 复制 Poetry 配置文件
RUN echo "Copying Poetry configuration files..."
COPY pyproject.toml poetry.lock ./
RUN echo "Poetry configuration files copied successfully"

# 安装 setuptools
RUN echo "Installing setuptools..."
RUN pip install setuptools && echo "Setuptools installed successfully"

# 安装依赖
RUN echo "Installing dependencies using Poetry..."
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi && \
    echo "Dependencies installed successfully"

# 复制启动脚本
RUN echo "Starting to copy startup.sh..."
COPY startup.sh /app/
RUN echo "Copied startup.sh to /app" && \
    chmod +x /app/startup.sh && \
    echo "Made startup.sh executable" && \
    ls -l /app/startup.sh


# 使用脚本启动容器
CMD ["/app/startup.sh"]
