from django.db import models
from django.db.models import JSONField
from django.utils import timezone

# Task: Định nghĩa một công việc crawl
class Task(models.Model):
	CRAWL_TYPE_CHOICES = [
		("listing", "Listing"),
		("job_detail", "Job Detail"),
	]
	name = models.CharField(max_length=255)
	url = models.URLField()
	active = models.BooleanField(default=True)
	crawl_type = models.CharField(max_length=32, choices=CRAWL_TYPE_CHOICES, default="listing")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return self.name

# Run: Một phiên chạy crawl cụ thể của task
class Run(models.Model):
	STATUS_CHOICES = [
		("pending", "Pending"),
		("running", "Running"),
		("done", "Done"),
		("error", "Error"),
	]
	task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="runs")
	status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
	started_at = models.DateTimeField(default=timezone.now)
	finished_at = models.DateTimeField(null=True, blank=True)
	item_count = models.PositiveIntegerField(default=0)
	error_message = models.TextField(blank=True, null=True)

	def __str__(self):
		return f"Run {self.id} for {self.task.name} ({self.status})"

# Item: Dữ liệu lấy được từ trang freelancer
class Item(models.Model):
	run = models.ForeignKey(Run, on_delete=models.CASCADE, related_name="items")
	task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="items")
	source_id = models.CharField(max_length=255, db_index=True)  # ID gốc trên freelancer
	title = models.CharField(max_length=500)
	budget = models.CharField(max_length=255, blank=True, null=True)
	skills = models.CharField(max_length=500, blank=True, null=True)
	description = models.TextField(blank=True, null=True)
	url = models.URLField(max_length=500, blank=True, null=True, unique=True)
	data = JSONField(default=dict)  # Lưu toàn bộ dữ liệu crawl dạng JSON
	created_at = models.DateTimeField(auto_now_add=True)
	pushed = models.BooleanField(default=False)
	day_left = models.CharField(max_length=100, blank=True, null=True)
	score = models.FloatField(null=True, blank=True)  # AI Chấm điểm

	class Meta:
		unique_together = ("task", "source_id")

	def __str__(self):
		return self.title

# PushConfig: Cấu hình đẩy dữ liệu ra API bên ngoài
class PushConfig(models.Model):
	task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name="push_config", null=True, blank=True)
	enabled = models.BooleanField(default=False)
	endpoint = models.URLField(blank=True, null=True)
	token = models.CharField(max_length=255, blank=True, null=True)
	is_global = models.BooleanField(default=False)

	def __str__(self):
		return f"PushConfig for {self.task.name if self.task else 'Global'}"

# PushLog: Lịch sử gửi từng item dữ liệu lên API
class PushLog(models.Model):
	item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="push_logs")
	pushed_at = models.DateTimeField(auto_now_add=True)
	success = models.BooleanField(default=False)
	http_status = models.IntegerField(null=True, blank=True)
	response = models.TextField(blank=True, null=True)

	def __str__(self):
		return f"PushLog for {self.item.title} at {self.pushed_at}"

# Create your models here.
