FROM public.ecr.aws/lambda/python:3.13

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy dependency metadata first (layer caching)
COPY pyproject.toml uv.lock ./

# Install uv
RUN pip install --no-cache-dir uv

# Install dependencies into the Lambda runtime
RUN uv sync

# Copy application code
COPY src/ ./src/

# Lambda handler
CMD ["data_platform.lambda_handler.handler"]
