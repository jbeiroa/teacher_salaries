FROM public.ecr.aws/lambda/python:3.12

# Install poetry
RUN pip install poetry==1.8.3

# Copy project files
COPY pyproject.toml poetry.lock ${LAMBDA_TASK_ROOT}/

# Install dependencies without creating a virtualenv so they go into system python
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main

# Copy application code and artifacts
COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY artifacts/ ${LAMBDA_TASK_ROOT}/artifacts/
COPY reports/ ${LAMBDA_TASK_ROOT}/reports/

# Ensure the src directory is in the PYTHONPATH
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}/src:${LAMBDA_TASK_ROOT}"

# Set the CMD to your handler
CMD [ "src.salary_app.handler" ]