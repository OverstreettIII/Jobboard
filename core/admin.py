from django.contrib import admin
from .models import Task, Run, Item, PushConfig, PushLog

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "url", "active", "crawl_type", "created_at", "updated_at")
	search_fields = ("name", "url")
	list_filter = ("active", "crawl_type")
	ordering = ("-created_at",)

@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
	list_display = ("id", "task", "status", "started_at", "finished_at", "item_count")
	list_filter = ("status", "task")
	search_fields = ("task__name",)
	ordering = ("-started_at",)

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
	list_display = (
		"id", "title", "task", "run", "source_id", "score", "budget", "created_at", "pushed"
	)
	search_fields = ("title", "source_id", "task__name")
	list_filter = ("task", "pushed")
	ordering = ("-created_at",)

@admin.register(PushConfig)
class PushConfigAdmin(admin.ModelAdmin):
	list_display = ("id", "task", "enabled", "endpoint", "is_global")
	list_filter = ("enabled", "is_global")
	search_fields = ("endpoint",)

@admin.register(PushLog)
class PushLogAdmin(admin.ModelAdmin):
	list_display = ("id", "item", "pushed_at", "success", "http_status")
	list_filter = ("success",)
	search_fields = ("item__title",)
