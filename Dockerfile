FROM python:3.13.17

ENV APP_HOME=/app
WORKDIR $APP_HOME

COPY . ./

RUN python -m pip install --no-cache-dir -r requirements.txt

ENV PORT=8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 -k uvicorn.workers.UvicornWorker app:app 
