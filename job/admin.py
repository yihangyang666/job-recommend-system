from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import JobData, UserList, UserExpect, SpiderInfo
from bson import ObjectId
from job.tools import get_mongodb
from django.utils import timezone
from datetime import datetime

# 后台里面的认证和授权 可以隐藏掉
from django.contrib import admin
from django.contrib.auth.models import User, Group

# 取消注册 User 和 Group 模型
admin.site.unregister(User)
admin.site.unregister(Group)

# 设置管理后台的头部标题
admin.site.site_header = '招聘后台管理'
# 设置管理后台在浏览器标签页中显示的标题
admin.site.site_title = '招聘后台管理'
# 设置管理后台主页的标题
admin.site.index_title = '招聘后台管理'

@admin.register(JobData)
class JobDataAdmin(admin.ModelAdmin):
    list_display = ('job_id', 'name', 'company', 'salary', 'place', 'education', 'experience', 'company_size', 'created_at')
    list_filter = ('education', 'place', 'company_size')
    search_fields = ('name', 'company', 'place')
    ordering = ('-created_at',)
    
    def delete_model(self, request, obj):
        """处理单条记录删除"""
        try:
            # 连接 MongoDB
            db = get_mongodb()
            if db:
                # 从 MongoDB 删除记录
                db.job_datas.delete_one({'_id': ObjectId(obj.job_id)})
            # 删除 Django 数据库中的记录
            super().delete_model(request, obj)
            messages.success(request, '成功删除记录')
        except Exception as e:
            messages.error(request, f'删除失败: {str(e)}')
    
    def delete_queryset(self, request, queryset):
        """处理批量删除"""
        try:
            # 连接 MongoDB
            db = get_mongodb()
            if db:
                # 从 MongoDB 批量删除记录
                job_ids = [ObjectId(obj.job_id) for obj in queryset]
                db.job_datas.delete_many({'_id': {'$in': job_ids}})
            # 删除 Django 数据库中的记录
            super().delete_queryset(request, queryset)
            messages.success(request, '成功批量删除记录')
        except Exception as e:
            messages.error(request, f'批量删除失败: {str(e)}')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync_mongodb/', self.sync_mongodb, name='sync_mongodb'),
        ]
        return custom_urls + urls
    
    def sync_mongodb(self, request):
        try:
            JobData.sync_from_mongodb()
            self.message_user(request, "成功从MongoDB同步数据", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"同步数据失败: {str(e)}", messages.ERROR)
        return HttpResponseRedirect("../")
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_sync_button'] = True
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(UserList)
class UserListAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'user_name')
    search_fields = ('user_id', 'user_name')

@admin.register(UserExpect)
class UserExpectAdmin(admin.ModelAdmin):
    list_display = ('user', 'key_word', 'place')
    list_filter = ('place',)
    search_fields = ('user__user_name', 'key_word', 'place')

@admin.register(SpiderInfo)
class SpiderInfoAdmin(admin.ModelAdmin):
    list_display = ('spider_id', 'count', 'page')


