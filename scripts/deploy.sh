#! /bin/bash
echo "changing directory" | systemd-cat
cd /home/zeeshan/moviepedia
echo `pwd` | systemd-cat

echo "git pull" | systemd-cat
sudo /usr/bin/git pull
echo "ok" | systemd-cat

echo "pipenv sync" | systemd-cat
/home/zeeshan/.local/bin/pipenv sync
echo "ok" | systemd-cat
echo "pipenv clean" | systemd-cat
/home/zeeshan/.local/bin/pipenv clean
echo "ok" | systemd-cat

echo "pipenv run python manage.py check --deploy" | systemd-cat
/home/zeeshan/.local/bin/pipenv run python manage.py check --deploy
echo "ok" | systemd-cat

# pipenv run python manage.py migrate --noinput

echo "pipenv run python manage.py collectstatic --noinput -c" | systemd-cat
/home/zeeshan/.local/bin/pipenv run python manage.py collectstatic --noinput -c
echo "ok" | systemd-cat


echo "pipenv run python manage.py migrate --noinput" | systemd-cat
/home/zeeshan/.local/bin/pipenv run python manage.py migrate --noinput
echo "ok" | systemd-cat

echo "sudo service gunicorn restart" | systemd-cat
sudo /usr/sbin/service gunicorn restart
echo "ok" | systemd-cat