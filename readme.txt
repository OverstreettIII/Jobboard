python manage.py crawl_freelancer --task_id 1
docker-compose exec web bash
push API
>>> from core.push_api import push_all_items
>>> push_all_items()

db
docker exec -it jobboard-db-1 psql -U jobuser -d jobboard


vào docker 
docker exec -it jobboard-web-1 bash

push 3 item
python manage.py shell -c "from core.push_api import push_item; from core.models import Item; token='171|rpVj3ajnrLWMFfWg4rRiqbHg2VJ7swoBgBwWc9c89a879f28'; items = Item.objects.filter(pushed=False)[:3]; [push_item(item, token) for item in items]"

push all item
python manage.py shell -c "from core.push_api import push_item; from core.models import Item; token='171|rpVj3ajnrLWMFfWg4rRiqbHg2VJ7swoBgBwWc9c89a879f28'; items = Item.objects.filter(pushed=False); [push_item(item, token) for item in items]"