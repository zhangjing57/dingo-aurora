# 使用官方的Python运行时作为父镜像
FROM python:3.9
# 设置工作目录为/app
WORKDIR /app
# 将当前目录内容复制到位于 /app 的容器中
COPY . /
# 安装任何需要的包
RUN pip install torch-2.0.0+cpu-cp310-cp310-linux_x86_64.whl
RUN pip install torchvision-0.15.1+cpu-cp310-cp310-linux_x86_64.whl
RUN pip install --no-cache-dir -r requirements_new.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 将/etc/localtime链接到上海时区文件
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
# 对外暴露的端口号
EXPOSE 9700
# 定义环境变量
ENV model = gpt-4-vision-preview
# 当容器启动时运行python app.py
CMD ["python", "app.py"]

