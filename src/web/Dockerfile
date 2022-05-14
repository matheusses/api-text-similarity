#Install python with ubuntu - docker hb
FROM python:3
#commom diretory to run solution
WORKDIR /usr/src/app
#Copy dependencies to the working directory
COPY requirements.txt .
#run  pip install in requirements.txt file
#no cache directory
# -r =>  recursive
RUN pip install --no-cache-dir -r requirements.txt
#  copy files to the directory system
COPY . .
RUN python -m spacy download en_core_web_sm

WORKDIR /usr/src/app
#CMD - telling docker run 
CMD ["python", "app.py"]