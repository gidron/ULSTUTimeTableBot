FROM python:3.13
RUN apt-get update && apt-get install -y tzdata fonts-dejavu-core fonts-noto-core
WORKDIR /app
COPY requirements.txt /app
RUN pip install -r requirements.txt
COPY . /app
CMD ["python", "bot.py"]
