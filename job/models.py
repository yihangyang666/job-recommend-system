# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = True` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.utils import timezone
from bson import ObjectId





from django.db import models

class JobData(models.Model):
    job_id = models.CharField(max_length=100, primary_key=True, verbose_name='职位编号')
    name = models.CharField(max_length=100, null=True, blank=True, verbose_name='职位名称')
    company = models.CharField(max_length=100, null=True, blank=True, verbose_name='公司名称')
    salary = models.CharField(max_length=50, null=True, blank=True, verbose_name='薪资待遇')
    place = models.CharField(max_length=50, null=True, blank=True, verbose_name='工作地点')
    education = models.CharField(max_length=50, null=True, blank=True, verbose_name='学历要求')
    experience = models.CharField(max_length=50, null=True, blank=True, verbose_name='工作经验')
    label = models.CharField(max_length=200, null=True, blank=True, verbose_name='职位标签')
    company_type = models.CharField(max_length=50, null=True, blank=True, verbose_name='公司类型')
    company_size = models.CharField(max_length=50, null=True, blank=True, verbose_name='公司规模')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')

    class Meta:
        verbose_name = '职位信息'
        verbose_name_plural = '职位信息'
        db_table = 'job_data'

    def __str__(self):
        return f"{self.name} - {self.company}"

    @classmethod
    def sync_from_mongodb(cls):
        """从MongoDB同步数据到Django模型"""
        from django.conf import settings
        from pymongo import MongoClient
        from bson import ObjectId
        
        # 连接MongoDB
        client = MongoClient(settings.MONGODB_URI)
        db = client[settings.MONGODB_NAME]
        
        # 获取MongoDB中的所有职位数据
        jobs = db.job_datas.find()
        
        # 清空当前表
        cls.objects.all().delete()
        
        # 批量创建新记录
        bulk_jobs = []
        for job in jobs:
            bulk_jobs.append(cls(
                job_id=str(job['_id']),
                name=job.get('name', ''),
                company=job.get('company', ''),
                salary=job.get('salary', ''),
                place=job.get('place', ''),
                education=job.get('education', ''),
                experience=job.get('experience', ''),
                label=job.get('label', ''),
                company_type=job.get('company_type', ''),
                company_size=job.get('company_size', '')
            ))
        
        if bulk_jobs:
            cls.objects.bulk_create(bulk_jobs)

class UserList(models.Model):
    user_id = models.CharField(max_length=20, primary_key=True, verbose_name='用户账号')
    user_name = models.CharField(max_length=20, verbose_name='用户昵称')
    pass_word = models.CharField(max_length=20, verbose_name='用户密码')

    class Meta:
        verbose_name = '用户信息'
        verbose_name_plural = '用户信息'
        db_table = 'user_list'

    def __str__(self):
        return self.user_name

class UserExpect(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(UserList, on_delete=models.CASCADE, verbose_name='用户账号')
    key_word = models.CharField(max_length=20, verbose_name='期望职位')
    place = models.CharField(max_length=20, verbose_name='期望城市')

    class Meta:
        verbose_name = '用户期望'
        verbose_name_plural = '用户期望'
        db_table = 'user_expect'

    def __str__(self):
        return f"{self.user.user_name} - {self.key_word}"

class SendList(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(UserList, on_delete=models.CASCADE, verbose_name='用户')
    job_id = models.CharField(max_length=255, verbose_name='职位ID')
    job_name = models.CharField(max_length=255, verbose_name='职位名称', null=True, blank=True)
    company = models.CharField(max_length=255, verbose_name='公司名称', null=True, blank=True)
    company_type = models.CharField(max_length=100, verbose_name='所属行业', null=True, blank=True)
    company_size = models.CharField(max_length=100, verbose_name='公司规模', null=True, blank=True)
    created_at = models.DateTimeField(verbose_name='投递时间')

    class Meta:
        verbose_name = '投递记录'
        verbose_name_plural = verbose_name
        db_table = 'send_list'
        ordering = ['-created_at']

    @property
    def job_info(self):
        """获取职位信息"""
        from job.tools import get_mongodb
        from bson import ObjectId
        try:
            db = get_mongodb()
            if db and self.job_id:
                try:
                    # 尝试转换为 ObjectId
                    job_id = ObjectId(self.job_id)
                    job_data = db.job_datas.find_one({'_id': job_id})
                    if job_data:
                        # 更新本地字段
                        if not self.job_name:
                            self.job_name = job_data.get('name', '未知职位')
                        if not self.company:
                            self.company = job_data.get('company', '未知公司')
                        if not self.company_type:
                            self.company_type = job_data.get('company_type', '暂无数据')
                        if not self.company_size:
                            self.company_size = job_data.get('company_size', '暂无数据')
                        self.save(update_fields=['job_name', 'company', 'company_type', 'company_size'])
                    return job_data
                except Exception as e:
                    print(f"Error converting job_id to ObjectId: {str(e)}")
            return None
        except Exception as e:
            print(f"Error getting job info: {str(e)}")
            return None

    def save(self, *args, **kwargs):
        """重写保存方法，确保时区正确并同步职位信息"""
        from django.utils import timezone
        if self.created_at and timezone.is_naive(self.created_at):
            self.created_at = timezone.make_aware(self.created_at)
        
        # 如果是新记录或者缺少职位信息，尝试从MongoDB获取
        if not self.job_name or not self.company:
            if 'update_fields' not in kwargs:  # 避免在更新特定字段时递归调用
                self.job_info  # 调用 property 来更新字段
            
        super().save(*args, **kwargs)

    @classmethod
    def sync_from_mongodb(cls):
        """从MongoDB同步投递记录数据到Django模型"""
        from django.conf import settings
        from pymongo import MongoClient
        from bson import ObjectId
        import datetime
        from django.utils import timezone
        
        # 连接MongoDB
        client = MongoClient(settings.MONGODB_URI)
        db = client[settings.MONGODB_NAME]
        
        # 获取MongoDB中的所有投递记录
        send_records = db.send_list.find()
        
        # 清空当前表
        cls.objects.all().delete()
        
        # 创建一个字典来存储用户ID到用户对象的映射
        from job.models import UserList
        user_dict = {user.user_id: user for user in UserList.objects.all()}
        
        # 创建新记录
        bulk_records = []
        for record in send_records:
            try:
                user_id = record.get('user_id', '')
                if not user_id or user_id not in user_dict:
                    continue
                
                # 获取用户
                user = user_dict[user_id]
                
                # 创建投递记录
                job_id = str(record['job_id']) if 'job_id' in record else None
                if not job_id:
                    continue
                
                # 尝试获取职位信息
                job_data = None
                try:
                    job_data = db.job_datas.find_one({'_id': ObjectId(job_id)})
                except Exception as e:
                    print(f"查找职位时出错: {str(e)}")
                
                # 确保时区正确
                created_at = record.get('created_at', datetime.datetime.now())
                if timezone.is_naive(created_at):
                    created_at = timezone.make_aware(created_at)
                
                # 创建SendList记录
                send_list = cls(
                    user=user,
                    job_id=job_id,
                    job_name=record.get('job_name', '') or (job_data.get('name', '未知职位') if job_data else '未知职位'),
                    company=record.get('company', '') or (job_data.get('company', '未知公司') if job_data else '未知公司'),
                    company_type=record.get('company_type', '') or (job_data.get('company_type', '') if job_data else ''),
                    company_size=record.get('company_size', '') or (job_data.get('company_size', '') if job_data else ''),
                    created_at=created_at
                )
                bulk_records.append(send_list)
            except Exception as e:
                print(f"处理投递记录时出错: {str(e)}")
        
        # 批量创建记录
        if bulk_records:
            cls.objects.bulk_create(bulk_records)
        
        return len(bulk_records)

class SpiderInfo(models.Model):
    spider_id = models.IntegerField(primary_key=True, verbose_name='爬虫编号')
    count = models.IntegerField(default=0, verbose_name='爬取次数')
    page = models.IntegerField(default=0, verbose_name='爬取页数')

    class Meta:
        verbose_name = '爬虫信息'
        verbose_name_plural = '爬虫信息'
        db_table = 'spider_info'

    def __str__(self):
        return f"爬虫{self.spider_id}"

