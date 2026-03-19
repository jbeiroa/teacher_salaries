FROM public.ecr.aws/lambda/python:3.12

# Install poetry
RUN pip install poetry==1.8.3

# Copy project files
COPY pyproject.toml poetry.lock ${LAMBDA_TASK_ROOT}/

# Install dependencies (only main group for app runtime)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main

# Copy application code (CONTENTS of src)
# This puts salary_app.py and salary_data/ at the root
COPY src/ ${LAMBDA_TASK_ROOT}/
COPY artifacts/ ${LAMBDA_TASK_ROOT}/artifacts/
COPY reports/ ${LAMBDA_TASK_ROOT}/reports/

# Ensure the task root is in the PYTHONPATH
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"

# Set the CMD to your handler (now without 'src.' prefix)
CMD [ "salary_app.handler" ]
