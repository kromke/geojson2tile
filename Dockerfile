FROM python

#ARG PYTHON_VERSION=3.12.6
#ARG GDAL_VERSION=3.9.2
#ARG SOURCE_DIR=/usr/local/src/python-gdal
#
#ENV PYENV_ROOT="/usr/local/pyenv"
#ENV PATH="/usr/local/pyenv/shims:/usr/local/pyenv/bin:$PATH"

RUN \
    # Install runtime dependencies
    apt update \
    && apt install -y \
        gdal-bin \
        gdal-data \
        gdal-plugins \
        libgdal-dev \
        python3-gdal

RUN mkdir "app"
WORKDIR /app

COPY ./src ./src
COPY ./main.py .
COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Command to run the application
CMD ["python", "main.py"]