# /bin/bash
echo "changing directory"
cd /home/zeeshan/moviepedia
echo `pwd`

echo "git pull origin master"
git pull origin master
echo "ok"

echo "pipenv run python manage.py check --deploy"
pipenv run python manage.py check --deploy
echo "ok"

# pipenv run python manage.py migrate --noinput
echo "pipenv run python manage.py collectstatic --noinput -c"
pipenv run python manage.py collectstatic --noinput -c
echo "ok"

echo "sudo service gunicorn restart"
sudo service gunicorn restart
echo "ok"