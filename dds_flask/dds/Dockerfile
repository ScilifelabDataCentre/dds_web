FROM python:3.6

EXPOSE 5000

WORKDIR /dds

COPY requirements.txt /dds
RUN pip install -r requirements.txt

COPY app.py /dds
CMD python app.py
