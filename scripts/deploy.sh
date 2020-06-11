#! /bin/bash
echo "changing directory" | systemd-cat
cd /home/zeeshan/moviepedia
echo `pwd` | systemd-cat

echo "git pull origin master" | systemd-cat
git pull origin master
echo "ok" | systemd-cat

echo "pipenv install" | systemd-cat
/home/zeeshan/.local/bin/pipenv install
echo "ok" | systemd-cat

echo "pipenv run python manage.py check --deploy" | systemd-cat
/home/zeeshan/.local/bin/pipenv run python manage.py check --deploy
echo "ok" | systemd-cat

# pipenv run python manage.py migrate --noinput

echo "pipenv run python manage.py collectstatic --noinput -c" | systemd-cat
/home/zeeshan/.local/bin/pipenv run python manage.py collectstatic --noinput -c
echo "ok" | systemd-cat

echo "sudo service gunicorn restart" | systemd-cat
sudo service gunicorn restart
echo "ok" | systemd-cat