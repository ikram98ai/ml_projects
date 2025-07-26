FROM public.ecr.aws/lambda/python:3.12

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the specified packages
RUN pip install -r requirements.txt

# Create a directory for NLTK data and set permissions
RUN mkdir -p /usr/share/nltk_data
# Download NLTK data to the created directory
RUN python -m nltk.downloader -d /usr/share/nltk_data punkt_tab
# Set the NLTK_DATA environment variable
ENV NLTK_DATA=/usr/share/nltk_data

# Copy function code
COPY . ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "main.handler" ]