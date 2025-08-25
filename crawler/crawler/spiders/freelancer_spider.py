import os
import sys
import django
import threading
from django.db import close_old_connections

# Thiết lập môi trường Django để có thể thao tác với DB từ Scrapy spider
sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobboard.settings")
django.setup()

from core.models import Item, Task, Run

import scrapy
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

def get_job_score(title, description, skills, api_key):
    """Chấm điểm job bằng AI, trả về số điểm (float) hoặc None nếu lỗi."""
    client = OpenAI(api_key=api_key)
    prompt = (
        "Bạn là chuyên gia tuyển dụng IT. "
        "Hãy chấm điểm mức độ hấp dẫn và phù hợp của job sau trên thang điểm 1-10. "
        "Chỉ trả về số điểm, không giải thích.\n"
        f"Tiêu đề: {title}\nMô tả: {description}\nKỹ năng: {skills}"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        score = response.choices[0].message.content.strip()
        score = float(score)
    except Exception as e:
        print(f"AI scoring error: {e}")
        score = None
    return score

class FreelancerSpider(scrapy.Spider):
    new_count = 0
    exist_count = 0
    name = "freelancer_spider"
    allowed_domains = ["freelancer.com"]

    def start_requests(self):
        """Khởi tạo crawl từ 3 trang đầu tiên."""
        base_url = getattr(self, 'base_url', None)
        if not base_url:
            raise ValueError("base_url phải được truyền vào spider!")
        print(f"[DEBUG] Using base_url: {base_url}")
        for page in range(1, 4):  # Crawl 3 trang đầu
            if page == 1:
                url = base_url
            else:
                if base_url.endswith('/'):
                    url = f"{base_url}{page}"
                else:
                    url = f"{base_url}/{page}"
            print(f"[DEBUG] Crawling page {page} at URL: {url}")
            yield scrapy.Request(url=url, callback=self.parse, meta={'page': page})

    def parse(self, response):
        """Parse trang danh sách job, lấy thông tin từng job."""
        run_id = os.environ.get('FREELANCER_RUN_ID')
        task_id = os.environ.get('FREELANCER_TASK_ID')
        page = response.meta.get('page', 1)
        print(f"[DEBUG] Đang crawl URL: {response.url}")
        jobs = response.css('div.JobSearchCard-item')
        print(f"[DEBUG] Page {page}: {len(jobs)} jobs found")
        for job in jobs:
            title = job.css('a.JobSearchCard-primary-heading-link::text').get(default='').strip()
            url = job.css('a.JobSearchCard-primary-heading-link::attr(href)').get()
            url = response.urljoin(url) if url else ''
            days_left = job.css('span.JobSearchCard-primary-heading-days::text').get(default='').strip()
            skills = job.css('div.JobSearchCard-primary-tags a.JobSearchCard-primary-tagsLink::text').getall()
            source_id = url.split('/')[-1]

            job_data = {
                'title': title,
                'url': url,
                'days_left': days_left,
                'skills': ', '.join(skills),
                'source_id': source_id,
                'run_id': run_id,
                'task_id': task_id,
            }
            print(f"[DEBUG] Crawl job: {title} | {url}")
            yield scrapy.Request(url=url, callback=self.parse_detail, meta={'job_data': job_data})

    def parse_detail(self, response):
        """Parse trang chi tiết job, lấy budget, description và chấm điểm AI."""
        job = response.meta['job_data']
        budget = response.css('div[data-hide-mobile="true"] h2.ng-star-inserted::text').get(default='').strip()
        description_detail = response.css('p.Project-description.whitespace-pre-line::text').get(default='').strip()
        api_key = os.environ.get('OPENAI_API_KEY')
        score = get_job_score(job['title'], description_detail, job['skills'], api_key)

        def save_item_thread():
            run = Run.objects.filter(id=job['run_id']).first() if job['run_id'] else None
            task = Task.objects.filter(id=job['task_id']).first() if job['task_id'] else None
            try:
                obj, created = Item.objects.update_or_create(
                    url=job['url'],
                    defaults={
                        'run': run,
                        'title': job['title'],
                        'budget': budget,
                        'skills': job['skills'],
                        'description': description_detail,
                        'day_left': job['days_left'],
                        'source_id': job['source_id'],
                        'task': task,
                        'score': score,
                    }
                )
                print(f"Saving item: url={job['url']}, score={score}, source_id={job['source_id']}, run_id={run.id if run else None}")
                if created:
                    type(self).new_count += 1
                    print(f"New item: {job['url']}")
                else:
                    type(self).exist_count += 1
                    print(f"Existing item: {job['url']}")
            except Exception as e:
                print(f"Error saving item: {e}")
            close_old_connections()
        t = threading.Thread(target=save_item_thread)
        t.start()

    def closed(self, reason):
        """In tổng số job mới và job đã tồn tại khi spider kết thúc."""
        print(f"Summary: {self.new_count} new items, {self.exist_count} existing items.")
