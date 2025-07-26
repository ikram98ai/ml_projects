FROM public.ecr.aws/lambda/python:3.12

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install packages
RUN pip install -r requirements.txt

# Create directory for NLTK data with WRITE permissions
RUN mkdir -p /usr/share/nltk_data && chmod a+rwx /usr/share/nltk_data

# Download REQUIRED NLTK datasets
RUN python -m nltk.downloader -d /usr/share/nltk_data punkt stopwords

# Set environment variable
ENV NLTK_DATA=/usr/share/nltk_data

# Copy application code
COPY . ${LAMBDA_TASK_ROOT}

CMD [ "main.handler" ]