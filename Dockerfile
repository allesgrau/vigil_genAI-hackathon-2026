FROM apify/actor-python:3.12

WORKDIR /usr/src/app

COPY requirements.txt ./
# For local development with Streamlit and tests, use:
# pip install -r requirements-dev.txt
RUN pip install -r requirements.txt

COPY . ./

ENV PYTHONPATH=/usr/src/app/src

CMD ["python", "src/main.py"]