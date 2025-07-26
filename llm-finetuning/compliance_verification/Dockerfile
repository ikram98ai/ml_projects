FROM public.ecr.aws/lambda/python:3.12

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install packages
RUN pip install -r requirements.txt

# Create a directory for NLTK data and set permissions
RUN mkdir -p /usr/share/nltk_data
# Download NLTK data to the created directory
RUN python -c "import nltk; nltk.download('punkt_tab', download_dir='/usr/share/nltk_data')"
RUN python -c "import nltk; nltk.download('stopwords', download_dir='/usr/share/nltk_data')"
# Set the NLTK_DATA environment variable
ENV NLTK_DATA=/usr/share/nltk_data

# Copy function code
COPY . ${LAMBDA_TASK_ROOT}

CMD [ "main.handler" ]