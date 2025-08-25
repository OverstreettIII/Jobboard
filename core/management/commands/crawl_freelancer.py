from django.core.management.base import BaseCommand
from core.models import Run, Task
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import sys, os

class Command(BaseCommand):
    help = 'Crawl freelancer.com jobs and save to DB with Run tracking.'

    def add_arguments(self, parser):
        parser.add_argument('--task_id', type=int, required=True, help='ID của Task cần crawl')

    def handle(self, *args, **options):
        task = Task.objects.get(id=options['task_id'])
        # Tạo Run mới
        run = Run.objects.create(task=task, status='running', item_count=0)
        self.stdout.write(self.style.SUCCESS(f'Created Run {run.id}'))

        # Truyền run_id và task_id vào spider qua biến môi trường
        os.environ['FREELANCER_RUN_ID'] = str(run.id)
        os.environ['FREELANCER_TASK_ID'] = str(task.id)

        import os as _os
        _os.chdir('crawler')  # Chuyển vào thư mục Scrapy project
        sys.path.append(os.path.abspath('.'))
        process = CrawlerProcess(get_project_settings())
        process.crawl('freelancer_spider', base_url=task.url)
        process.start()

        # Sau khi crawl xong, cập nhật trạng thái Run
        _os.chdir('..')  # Quay lại thư mục gốc Django project
        run.refresh_from_db()
        run.status = 'done'
        run.item_count = run.items.count()
        run.save()
        self.stdout.write(self.style.SUCCESS(f'Run {run.id} finished, {run.item_count} items crawled.'))
