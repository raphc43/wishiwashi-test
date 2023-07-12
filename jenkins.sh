#!/bin/bash

# Common environment variables for running unit tests
export STRIPE_API_KEY="sk_test_5OD9yinDX5BZqwVAyz4GKXZq"  # Test account
export STRIPE_PUBLISHABLE_KEY="pk_test_ncQmoeph4MSrDS9gZgDSM2zO"  # Test account
export RENDER_SERVICE_USERNAME="username"
export RENDER_SERVICE_PASSWORD="testing"
export COMMUNICATE_SERVICE_USERNAME="username"
export COMMUNICATE_SERVICE_PASSWORD="testing"
export REDIS_URL="redis://"

test_commit() {
  VENV_LOCATION=/tmp/venv_commit

  if [ -d "$VENV_LOCATION" ]; then
    rm -fr "$VENV_LOCATION"
  fi
  virtualenv $VENV_LOCATION
  source $VENV_LOCATION/bin/activate
  pip install -r requirements-dev.txt \
      --download-cache=/tmp/.pip-download-cache \
      --find-links=file:///tmp/.pip-accel-sources
  pip freeze

  cd wishiwashi && python manage.py collectstatic --noinput

  if [[ -n $(git ls-files --other --exclude-standard --directory) ]];then
      echo "Untracked files"
      git ls-files --other --exclude-standard --directory
      exit 1
  fi
  export DATABASE_URL='postgres://wishiwashi_user:password@127.0.0.1:5432/wishiwashi_db'

  py.test --cov-report= --cov=. --cov-fail-under=70

  if [ $? -ne 0 ]; then
    echo "Code coverage must be 70% or higher"
    exit 1
  fi

  deactivate
}

test_and_deploy_staging() {
  # Test & deploy staging
  # =====================
  VENV_LOCATION=/tmp/venv_staging
  STAGING_FOLDER=/tmp/staging

  if [ -d "$VENV_LOCATION" ]; then
    rm -fr "$VENV_LOCATION"
  fi
  virtualenv $VENV_LOCATION
  source $VENV_LOCATION/bin/activate

  if [ -d "$STAGING_FOLDER" ]; then
    rm -fr "$STAGING_FOLDER"
  fi

  mkdir -p "$STAGING_FOLDER"
  cd $STAGING_FOLDER

  git clone -b staging --single-branch \
      git@github.com:wishiwashi/backend.git .

  pip install -r requirements-dev.txt \
      --download-cache=/tmp/.pip-download-cache \
      --find-links=file:///tmp/.pip-accel-sources
  pip freeze

  export DATABASE_URL='postgres://wishiwashi_user:password@127.0.0.1:5432/wishiwashi_db'

  cd wishiwashi && py.test --cov-report= --cov=. --cov-fail-under=70

  if [ $? -ne 0 ]; then
    echo "The staging branch's code coverage must be 70% or higher"
    exit 1
  fi

  deactivate

  heroku git:remote --app aqueous-spire-6501
  git push heroku staging:master

  if [ $? -ne 0 ]; then
    echo "Push to heroku failed"
    exit 1
  fi

  /usr/bin/s3cmd sync static/ s3://wishiwashi-backend-staging \
    --acl-public --guess-mime-type \
    --config=/var/lib/jenkins/.s3cfg.staging

  /usr/bin/s3cmd put --recursive --acl-public \
      --add-header='Cache-Control:max-age=31536000, public' \
      --add-header="Expires:`date -u +"%a, %d %b %Y %H:%M:%S GMT" \
      --date "next Year"`" static/ \
      s3://wishiwashi-backend-staging/ \
      --guess-mime-type --config=/var/lib/jenkins/.s3cfg.staging
}

test_and_deploy_master() {
  # Test & deploy staging
  # =====================
  VENV_LOCATION=/tmp/venv_master
  MASTER_FOLDER=/tmp/master

  if [ -d "$VENV_LOCATION" ]; then
    rm -fr "$VENV_LOCATION"
  fi
  virtualenv $VENV_LOCATION
  source $VENV_LOCATION/bin/activate

  if [ -d "$MASTER_FOLDER" ]; then
    rm -fr "$MASTER_FOLDER"
  fi

  mkdir -p "$MASTER_FOLDER"
  cd $MASTER_FOLDER

  git clone -b master --single-branch \
      git@github.com:wishiwashi/backend.git .

  pip install -r requirements-dev.txt \
      --download-cache=/tmp/.pip-download-cache \
      --find-links=file:///tmp/.pip-accel-sources
  pip freeze

  export DATABASE_URL='postgres://wishiwashi_user:password@127.0.0.1:5432/wishiwashi_db_master_branch'

  cd wishiwashi && py.test --cov-report= --cov=. --cov-fail-under=70

  if [ $? -ne 0 ]; then
    echo "The masters branch's code coverage must be 70% or higher"
    exit 1
  fi

  deactivate

  heroku git:remote --app polar-escarpment-4510
  git push heroku master

  if [ $? -ne 0 ]; then
    echo "Push to heroku failed"
    exit 1
  fi

  /usr/bin/s3cmd sync static/ s3://wishiwashi-backend-production \
    --acl-public --guess-mime-type \
    --config=/var/lib/jenkins/.s3cfg.master

  /usr/bin/s3cmd put --recursive --acl-public \
      --add-header='Cache-Control:max-age=31536000, public' \
      --add-header="Expires:`date -u +"%a, %d %b %Y %H:%M:%S GMT" \
      --date "next Year"`" static/ \
      s3://wishiwashi-backend-production/ \
      --guess-mime-type --config=/var/lib/jenkins/.s3cfg.master
}

# When deploying to prod pass 'master' when executing this script so it's
# obvious that you want to deploy to production
if [ $# -ne 1 ]; then
  test_commit
  test_and_deploy_staging
else
  test_and_deploy_master
fi

