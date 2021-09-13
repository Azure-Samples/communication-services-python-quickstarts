FROM python:3.9

RUN mkdir -p /code
WORKDIR /code
ADD . /code
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "/code/App.py"]
