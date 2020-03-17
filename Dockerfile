FROM python:3.7-onbuild

EXPOSE 5000

CMD [ "python", "./main.py" ]