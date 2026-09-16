#!/bin/bash
# Chạy Background Task Worker ngầm (Redis RQ)
python manage.py rqworker default &

# Chạy Indexer ngầm
python indexer/indexer.py &

# Chạy Django Web Server
daphne -b 0.0.0.0 -p $PORT core.asgi:application
