FROM python:3.8.0-alpine

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONBUFFERED 1

RUN pip install --upgrade pip
COPY . /usr/src/app/

COPY ./requirements.txt .
RUN pip install -r requirements.txt

RUN mkdir /code
COPY . /CODE/

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]


