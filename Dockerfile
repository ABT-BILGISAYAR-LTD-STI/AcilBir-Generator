FROM python:3.13-alpine

RUN adduser -D user

WORKDIR /opt/rdgen

# Copy files with correct ownership before switching to non-root
COPY --chown=user:user . .

# WORKDIR is owned by root — user needs write access for db.sqlite3
RUN chown user:user /opt/rdgen

# Pre-create folders so named volumes inherit user:user ownership
RUN mkdir -p /opt/rdgen/exe /opt/rdgen/png /opt/rdgen/temp_zips /opt/rdgen/downloads \
 && chown -R user:user /opt/rdgen/exe /opt/rdgen/png /opt/rdgen/temp_zips /opt/rdgen/downloads

USER user

RUN pip install --no-cache-dir --user -r requirements.txt \
 && python manage.py migrate

ENV PYTHONUNBUFFERED=1
ENV PATH="/home/user/.local/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=5)" || exit 1

CMD ["gunicorn", "-c", "gunicorn.conf.py", "rdgen.wsgi:application"]
