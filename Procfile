web: bin/start-nginx gunicorn -c config/gunicorn.conf --pythonpath wishiwashi base.wsgi --log-level info --log-file -
celerybeat: cd wishiwashi; celery beat --loglevel=INFO --app=base.celery.app
celeryworker: cd wishiwashi; celery worker --loglevel=INFO --app=base.celery.app
