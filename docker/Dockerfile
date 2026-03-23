# 使用官方 Python 运行时作为基础镜像, bullseye版本比纯slim版本更稳定
FROM python:3.10-slim-bullseye
# 设置环境变量
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE=api.settings.settings

# 创建并设置工作目录
RUN mkdir /review_api
WORKDIR /review_api

# 直接重写 sources.list 使用国内阿里云源
RUN echo "deb http://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main non-free non-free-firmware contrib" >> /etc/apt/sources.list

# 安装系统依赖和监控工具
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    gcc \
    curl \
    netcat-openbsd \
    iputils-ping \
    wget \
    procps \
    htop \
    vim \
    git \
    && rm -rf /var/lib/apt/lists/*

# 设置 pip 国内源（清华源）
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
# 复制 requirements.txt 并安装 Python 依赖
COPY ../requirements.txt /review_api/
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目文件
COPY ../api /review_api/api
COPY ../manage.py /review_api/
COPY ../uwsgi.ini /review_api/
COPY ../entrypoint.sh /review_api/
COPY ../docker/health.sh /usr/local/bin/
COPY ../static /review_api/static

# 做健康检查
RUN chmod +x /usr/local/bin/health.sh
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /usr/local/bin/health.sh

# 暴露端口
EXPOSE 8000

RUN chmod +x /review_api/entrypoint.sh
ENTRYPOINT ["/review_api/entrypoint.sh"]

