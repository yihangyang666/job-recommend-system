from django.shortcuts import render, redirect
from django.http import JsonResponse
# Create your views here.
from job import models
import re
from psutil import *
import numpy as np
from job import tools
from job import job_recommend
from collections import Counter
from pymongo import MongoClient
from django.conf import settings
from bson import json_util
import json
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login
from bson.objectid import ObjectId
from datetime import datetime
from collections import defaultdict

spider_code = 0  # 定义全局变量，用来识别爬虫的状态，0空闲，1繁忙


# python manage.py inspectdb > job/models.py
# 使用此命令可以将数据库表导入models生成数据模型


def standardize_job_title(keyword):
    """标准化职位名称，合并相似职位"""
    # 过滤掉城市名和无关词
    filtered_words = ['上海', '北京', '广州', '深圳', '杭州', '成都', '武汉', '南京', '西安', 
                     '公司', '有限', '股份', '集团', '企业', '招聘', '急聘', '诚聘', '高薪']
    
    # 如果关键词在过滤列表中，直接返回空字符串
    if keyword in filtered_words:
        return ''
    
    # 职位名称标准化映射
    standardization_map = {
        # Java相关
        'java': 'Java工程师',
        'java工程师': 'Java工程师',
        'java高级工程师': 'Java工程师',
        'java开发': 'Java工程师',
        'java开发工程师': 'Java工程师',
        '高级java': 'Java工程师',
        'java后端': 'Java工程师',
        'java后台': 'Java工程师',
        'java架构': 'Java工程师',
        
        # Python相关
        'python': 'Python工程师',
        'python工程师': 'Python工程师',
        'python开发': 'Python工程师',
        'python开发工程师': 'Python工程师',
        'python后端': 'Python工程师',
        'python后台': 'Python工程师',
        '高级python': 'Python工程师',
        
        # 数据分析相关
        '数据分析': '数据分析师',
        '数据分析师': '数据分析师',
        '数据分析工程师': '数据分析师',
        '高级数据分析师': '数据分析师',
        '数据': '数据分析师',
        'data': '数据分析师',
        'analyst': '数据分析师',
        
        # 算法相关
        '算法': '算法工程师',
        '算法工程师': '算法工程师',
        '机器学习': '算法工程师',
        'ai': '算法工程师',
        '人工智能': '算法工程师',
        '深度学习': '算法工程师',
        '计算机视觉': '算法工程师',
        'nlp': '算法工程师',
        
        # 前端相关
        '前端': '前端工程师',
        '前端开发': '前端工程师',
        '前端工程师': '前端工程师',
        'web': '前端工程师',
        'web前端': '前端工程师',
        'h5': '前端工程师',
        'javascript': '前端工程师',
        
        # 测试相关
        '测试': '测试工程师',
        '测试工程师': '测试工程师',
        '自动化测试': '测试工程师',
        'qa': '测试工程师',
        '质量': '测试工程师',
        
        # 运维相关
        '运维': '运维工程师',
        '运维工程师': '运维工程师',
        'devops': '运维工程师',
        'sre': '运维工程师',
        '系统工程师': '运维工程师',
        '网络工程师': '运维工程师',
        
        # C/C++相关
        'c++': 'C++工程师',
        'c/c++': 'C++工程师',
        'cpp': 'C++工程师',
        'c语言': 'C++工程师',
        'c': 'C++工程师',
        'C': 'C++工程师',
        'C语言': 'C++工程师',
        'C++': 'C++工程师',
        'C/C++': 'C++工程师',
        
        # 其他常见职位
        '自动驾驶': '自动驾驶工程师',
        '网络安全': '网络安全工程师',
        '安全工程师': '网络安全工程师',
        '网络安全工程师': '网络安全工程师',
        '专家': '技术专家',
        '开发工程师': '软件工程师',  # 将通用的开发工程师归类为软件工程师
    }
    
    # 移除关键词中的空格
    keyword = keyword.replace(' ', '')
    
    # 转换为小写进行匹配
    keyword_lower = keyword.lower()
    
    # 先尝试完全匹配
    if keyword_lower in standardization_map:
        return standardization_map[keyword_lower]
    
    # 如果没有完全匹配，尝试部分匹配
    for key, value in standardization_map.items():
        if key.lower() in keyword_lower:  # 确保key也转换为小写进行比较
            return value
            
    return keyword


def extract_job_keywords(job_title):
    """动态提取职位名称中的关键词"""
    # 移除特殊字符和多余空格
    job_title = re.sub(r'[^\w\s]', ' ', job_title)
    job_title = re.sub(r'\s+', ' ', job_title).strip()
    
    # 分割职位名称
    words = job_title.split()
    
    # 常见的职位后缀，用于分离主要关键词
    suffixes = ['工程师', '经理', '专员', '主管', '助理', '顾问', '师', '员']
    
    keywords = []
    current_word = ''
    
    for word in words:
        # 如果当前词是后缀，将其与之前的词组合
        if any(suffix in word for suffix in suffixes):
            if current_word:
                keywords.append(standardize_job_title(current_word + word))
                current_word = ''
            else:
                keywords.append(standardize_job_title(word))
        else:
            # 如果下一个词不是后缀，当前词直接作为关键词
            if current_word:
                keywords.append(standardize_job_title(current_word))
            current_word = word
    
    # 处理最后一个词
    if current_word:
        keywords.append(standardize_job_title(current_word))
    
    return keywords


def login(request):
    if request.method == "POST":
        user_id = request.POST.get('user')
        pass_word = request.POST.get('password')
        print('user------>', user_id)
        
        try:
            # 验证 Django 认证系统
            auth_user = authenticate(username=user_id, password=pass_word)
            
            if auth_user is None:
                return JsonResponse({'code': 1, 'msg': '账号或密码错误！'})
            
            # 检查自定义用户模型
            user = models.UserList.objects.filter(user_id=user_id).first()
            if not user:
                # 如果 auth_user 存在但 UserList 不存在，创建对应的 UserList 记录
                user = models.UserList.objects.create(
                    user_id=user_id,
                    user_name=auth_user.first_name or user_id,
                    pass_word=pass_word
                )
            
            # 登录 Django 认证系统
            auth_login(request, auth_user)
            
            # 保存session
            request.session['user_id'] = user_id
            request.session['user_name'] = user.user_name
            
            return JsonResponse({
                'code': 0,
                'msg': '登录成功！',
                'user_name': user.user_name
            })
            
        except Exception as e:
            print(f"登录时发生错误: {str(e)}")
            return JsonResponse({'code': 1, 'msg': '登录失败，请稍后重试！'})
    else:
        return render(request, "login.html")


def register(request):
    if request.method == "POST":
        user_id = request.POST.get('user')
        pass_word = request.POST.get('password')
        user_name = request.POST.get('user_name')
        
        try:
            # 检查用户ID是否已存在
            if models.UserList.objects.filter(user_id=user_id).exists():
                return JsonResponse({'code': 1, 'msg': '该账号已存在！'})
            
            # 同时创建 auth_user 和 UserList 用户
            auth_user = User.objects.create_user(
                username=user_id,
                password=pass_word,
                first_name=user_name
            )
            
            # 创建自定义用户模型
            user = models.UserList.objects.create(
                user_id=user_id,
                user_name=user_name,
                pass_word=pass_word
            )
            
            # 设置session
            request.session['user_id'] = user_id
            request.session['user_name'] = user_name
            
            return JsonResponse({'code': 0, 'msg': '注册成功！'})
            
        except Exception as e:
            print(f"注册时发生错误: {str(e)}")
            return JsonResponse({'code': 1, 'msg': '注册失败，请稍后重试！'})
    else:
        return render(request, "register.html")


# 退出(登出)
def logout(request):
    # 1. 将session中的用户名、昵称删除
    request.session.flush()
    # 2. 重定向到 登录界面
    return redirect('login')


def index(request):
    """此函数用于返回主页，主页包括头部，左侧菜单"""
    return render(request, "index.html")


def get_mongodb():
    """获取MongoDB连接"""
    try:
        client = MongoClient(settings.MONGODB_URI)
        db = client[settings.MONGODB_NAME]
        return db
    except Exception as e:
        print(f"MongoDB连接错误: {str(e)}")
        return None


def welcome(request):
    """此函数用于处理控制台页面"""
    try:
        # 连接MongoDB
        db = get_mongodb()
        if not db:
            return render(request, "welcome.html", {
                'all_job': 0,
                'mean_salary': 0,
                'job_data_1': {'name': '暂无数据', 'salary': '暂无数据'},
                'job_data_10': [],
                'spider_info': {'count': 0, 'page': 0}
            })

        # 从MongoDB获取所有职位数据
        job_data = list(db.job_datas.find())
        all_job = len(job_data)  # 职位信息总数

        if not job_data:
            return render(request, "welcome.html", {
                'all_job': 0,
                'mean_salary': 0,
                'job_data_1': {'name': '暂无数据', 'salary': '暂无数据'},
                'job_data_10': [],
                'spider_info': {'count': 0, 'page': 0}
            })

        list_1 = []  # 定义一个空列表
        for job in job_data:
            try:
                salary_str = job.get('salary', '')
                if not salary_str:  # 处理空值情况
                    job['salary_1'] = 0
                    list_1.append(0)
                    continue

                # 处理多种可能的薪资格式
                if '-' in salary_str:  # 处理范围格式 (例如: "10k-20k")
                    max_salary = re.findall(r'(\d+)k', salary_str)
                    if len(max_salary) >= 2:  # 如果找到两个数字，取第二个作为最高薪资
                        salary_1 = float(max_salary[1])
                    elif len(max_salary) == 1:  # 如果只找到一个数字
                        salary_1 = float(max_salary[0])
                    else:
                        salary_1 = 0
                else:  # 处理单个数值格式 (例如: "20k")
                    salary_match = re.findall(r'(\d+)k', salary_str)
                    salary_1 = float(salary_match[0]) if salary_match else 0

                job['salary_1'] = salary_1
                list_1.append(salary_1)
            except Exception as e:
                print(f"Error processing salary for job {job.get('_id', 'unknown')}: {str(e)}")
                job['salary_1'] = 0
                list_1.append(0)

        # 反向排序所有职位信息的最高薪资
        job_data = sorted(job_data, key=lambda x: x.get('salary_1', 0), reverse=True)
        job_data_10 = job_data[0:10]  # 取最高薪资前10用来渲染top-10表格
        job_data_1 = job_data[0]  # 取出最高薪资的职位信息
        mean_salary = int(np.mean(list_1)) if list_1 else 0  # 计算平均薪资

        # 查询爬虫程序运行的数据记录
        spider_info = models.SpiderInfo.objects.filter(spider_id=1).first()
        if not spider_info:
            spider_info = {'count': 0, 'page': 0}

        return render(request, "welcome.html", locals())

    except Exception as e:
        print(f"Error in welcome view: {e}")
        return render(request, "welcome.html", {
            'all_job': 0,
            'mean_salary': 0,
            'job_data_1': {'name': '暂无数据', 'salary': '暂无数据'},
            'job_data_10': [],
            'spider_info': {'count': 0, 'page': 0}
        })


def spiders(request):
    global spider_code
    # print(spider_code)
    spider_code_1 = spider_code
    return render(request, "spiders.html", locals())


def start_spider(request):
    if request.method == "POST":
        key_word = request.POST.get("key_word")
        city = request.POST.get("city")
        page = request.POST.get("page")
        role = request.POST.get("role")
        
        try:
            # 获取或创建爬虫信息记录
            spider_model, created = models.SpiderInfo.objects.get_or_create(
                spider_id=1,
                defaults={'count': 0, 'page': 0}
            )
            
            spider_code = 1  # 改变爬虫状态
            spider_model.count += 1  # 给次数+1
            spider_model.page += int(page)  # 给爬取页数加上选择的页数
            spider_model.save()
            
            # 记录爬取前的数据量
            db = get_mongodb()
            pre_count = db.job_datas.count_documents({}) if db else 0
            
            if role == '猎聘网':
                spider_code = tools.lieSpider(key_word=key_word, city=city, all_page=page)
        # elif role == '51job':
        #         spider_code = tools.job51Spider(key_word=key_word, city=city, all_page=page)
            
            # 计算爬取到的新数据量
            post_count = db.job_datas.count_documents({}) if db else 0
            new_data_count = post_count - pre_count
            
            return JsonResponse({
                "code": 0, 
                "msg": f"爬取完毕! 成功添加 {new_data_count} 条新职位数据。",
                "count": new_data_count
            })
            
        except Exception as e:
            print(f"Error in start_spider: {str(e)}")
            return JsonResponse({"code": 1, "msg": f"爬取失败: {str(e)}"})
    else:
        return JsonResponse({"code": 1, "msg": "请使用POST请求"})


def job_list(request):
    return render(request, "job_list.html", locals())


def get_job_list(request):
    """此函数用来渲染职位信息列表"""
    try:
        page = int(request.GET.get("page", "1"))
        limit = int(request.GET.get("limit", "15"))
        keyword = request.GET.get("keyword", "")
        price_min = request.GET.get("price_min", "")
        price_max = request.GET.get("price_max", "")
        edu = request.GET.get("edu", "")
        city = request.GET.get("city", "")

        # 连接MongoDB
        db = get_mongodb()
        if not db:
            return JsonResponse({"code": 1, "msg": "MongoDB连接失败", "count": 0, "data": []})

        # 构建查询条件
        query = {}
        if keyword:
            query['name'] = {'$regex': keyword, '$options': 'i'}
        if edu:
            query['education'] = {'$regex': edu, '$options': 'i'}
        if city:
            query['place'] = {'$regex': f'.*{city}.*', '$options': 'i'}

        # 从 job_datas 集合获取所有符合条件的职位
        job_data = list(db.job_datas.find(query))
        
        # 处理薪资过滤
        if price_min or price_max:
            filtered_jobs = []
            for job in job_data:
                try:
                    salary_str = job.get('salary', '')
                    if not salary_str:
                        continue
                    
                    # 处理薪资范围
                    salary_nums = re.findall(r'(\d+)k', salary_str)
                    if len(salary_nums) >= 2:
                        min_salary = float(salary_nums[0])
                        max_salary = float(salary_nums[1])
                    elif len(salary_nums) == 1:
                        min_salary = max_salary = float(salary_nums[0])
                    else:
                        continue
                    
                    # 根据薪资范围筛选
                    if price_min and not price_max:
                        if min_salary >= float(price_min):
                            filtered_jobs.append(job)
                    elif not price_min and price_max:
                        if max_salary <= float(price_max):
                            filtered_jobs.append(job)
                    elif price_min and price_max:
                        if float(price_min) <= min_salary and max_salary <= float(price_max):
                            filtered_jobs.append(job)
                except Exception as e:
                    print(f"Error processing salary for job {job.get('_id', 'unknown')}: {str(e)}")
                    continue
            job_data = filtered_jobs

        # 分页处理
        total_count = len(job_data)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        job_data_page = job_data[start_index:end_index]

        # 处理投递状态和格式化数据
        user_id = request.session.get("user_id")
        formatted_jobs = []
        
        # 获取用户已投递的职位ID列表
        sent_job_ids = []
        if user_id:
            sent_records = db.send_list.find({'user_id': user_id})
            sent_job_ids = [str(record['job_id']) for record in sent_records]
        
        for job in job_data_page:
            try:
                # 处理公司名称，确保显示合适长度
                company_name = job.get('company', '未知')
                if len(company_name) > 20:  # 如果公司名称过长，截取前20个字符
                    company_name = company_name[:17] + '...'
                
                # 构建职位数据
                formatted_job = {
                    '_id': str(job.get('_id', '')),  # MongoDB的_id字段
                    'job_id': str(job.get('_id', '')),  # 添加job_id字段
                    'name': job.get('name', '未知职位'),
                    'salary': job.get('salary', '薪资未知'),
                    'place': job.get('place', '地点未知'),
                    'education': job.get('education', '学历未知'),
                    'experience': job.get('experience', '经验未知'),
                    'company': company_name,
                    'company_type': job.get('company_type', '行业未知'),
                    'company_size': job.get('company_size', '规模未知'),
                    'href': job.get('href', ''),
                    'send_key': 0,
                    'status': ''
                }
                
                # 检查投递状态
                if str(job.get('_id', '')) in sent_job_ids:
                    formatted_job['send_key'] = 1
                    formatted_job['status'] = '已投递'
                    
                formatted_jobs.append(formatted_job)
                
            except Exception as e:
                print(f"Error formatting job {job.get('_id', 'unknown')}: {str(e)}")
                continue

        response_data = {
            "code": 0,
            "msg": "success" if total_count > 0 else "暂无数据",
            "count": total_count,
            "data": formatted_jobs
        }
        
        return JsonResponse(response_data, safe=False)  # 设置 safe=False 允许非字典对象序列化

    except Exception as e:
        print(f"Error in get_job_list: {str(e)}")
        return JsonResponse({
            "code": 1,
            "msg": f"服务器错误: {str(e)}",
            "count": 0,
            "data": []
        })


def get_psutil(request):
    """此函数用于读取cpu使用率和内存占用率"""
    # cpu_percent()可以获取cpu的使用率，参数interval是获取的间隔
    # virtual_memory()[2]可以获取内存的使用率
    return JsonResponse({'cpu_data': cpu_percent(interval=1), 'memory_data': virtual_memory()[2]})


def get_pie(request):
    """此函数用于处理饼图数据"""
    try:
        # 连接MongoDB
        db = get_mongodb()
        if not db:
            return JsonResponse({
                'edu_data': [],
                'salary_data': [],
                'msg': 'MongoDB连接失败'
            })

        # 从MongoDB获取所有职位数据
        job_data = list(db.job_datas.find())
        
        if not job_data:
            return JsonResponse({
                'edu_data': [],
                'salary_data': [],
                'msg': '暂无数据'
            })
            
            # 统计学历分布
        edu_list = ['博士', '硕士', '本科', '大专', '不限']
        edu_data = []
        for edu in edu_list:
                edu_count = len([job for job in job_data if edu in job.get('education', '')])
                if edu_count > 0:  # 只添加有数据的学历
                    edu_data.append({'name': edu, "value": edu_count})
        
        # 统计薪资分布
        salary_ranges = {
            '5K及以下': (0, 5),
            '5-10K': (5, 10),
            '10K-15K': (10, 15),
            '15K-20K': (15, 20),
            '20K-30K': (20, 30),
            '30-50K': (30, 50),
            '50K以上': (50, float('inf'))
        }
        
        salary_counts = {range_name: 0 for range_name in salary_ranges}
        
        for job in job_data:
            try:
                salary_str = job.get('salary', '')
                if not salary_str:
                    continue
                
                # 处理多种可能的薪资格式
                if '-' in salary_str:  # 处理范围格式 (例如: "10k-20k")
                    salary_nums = re.findall(r'(\d+)k', salary_str)
                    if len(salary_nums) >= 2:  # 如果找到两个数字，取第二个作为最高薪资
                        salary = float(salary_nums[1])
                    elif len(salary_nums) == 1:  # 如果只找到一个数字
                        salary = float(salary_nums[0])
                    else:
                        continue
                else:  # 处理单个数值格式 (例如: "20k")
                    salary_match = re.findall(r'(\d+)k', salary_str)
                    if not salary_match:
                        continue
                    salary = float(salary_match[0])
                
                # 将薪资分配到对应范围
                for range_name, (min_val, max_val) in salary_ranges.items():
                    if min_val <= salary <= max_val:
                        salary_counts[range_name] += 1
                        break
            except Exception as e:
                    print(f"Error processing salary for job {job.get('_id', 'unknown')}: {str(e)}")
                    continue
        
        # 转换为前端需要的格式，只包含有数据的范围
        salary_data = [
            {'name': name, 'value': count}
            for name, count in salary_counts.items()
            if count > 0
        ]
        
        return JsonResponse({
            'edu_data': edu_data,
            'salary_data': salary_data
        })
        
    except Exception as e:
        print(f"Error in get_pie view: {e}")
        return JsonResponse({
            'edu_data': [],
            'salary_data': [],
            'msg': f'服务器错误: {str(e)}'
        })


def send_job(request):
    """此函数用于投递职位和取消投递"""
    if request.method == "POST":
        user_id = request.session.get("user_id")
        job_id = request.POST.get("job_id")  # 这是 MongoDB 中的 _id
        send_key = request.POST.get("send_key")
        
        try:
            print(f"处理投递请求: user_id={user_id}, job_id={job_id}, send_key={send_key}")
            
            # 检查用户是否存在
            try:
                user = models.UserList.objects.get(user_id=user_id)
            except models.UserList.DoesNotExist:
                return JsonResponse({"Code": 1, "msg": "用户不存在"})
            
            # 连接MongoDB
            db = get_mongodb()
            if not db:
                return JsonResponse({"Code": 1, "msg": "数据库连接失败"})
            
            if int(send_key) == 1:
                # 取消投递 - 删除记录流程
                mongo_deleted = False
                django_deleted = False
                
                # 1. 先尝试从MongoDB删除
                try:
                    # 记录额外信息用于日志
                    mongo_records = list(db.send_list.find({'user_id': user_id, 'job_id': job_id}))
                    mongo_count = len(mongo_records)
                    print(f"找到MongoDB匹配记录: {mongo_count}条")
                    
                    # 尝试精确匹配删除
                    result1 = db.send_list.delete_one({
                        'user_id': user_id,
                        'job_id': job_id
                    })
                    
                    # 记录第一次删除结果
                    if result1.deleted_count > 0:
                        mongo_deleted = True
                        print(f"MongoDB精确匹配删除成功: {result1.deleted_count}条")
                except Exception as e:
                    print(f"MongoDB删除异常: {str(e)}")
                
                # 2. 再删除Django数据库记录
                try:
                    # 记录删除前的记录数量
                    django_records = models.SendList.objects.filter(user=user, job_id=job_id)
                    django_count = django_records.count()
                    print(f"找到Django匹配记录: {django_count}条")
                    
                    if django_count > 0:
                        django_records.delete()
                        django_deleted = True
                        print(f"Django数据库删除成功: {django_count}条")
                    else:
                        print("Django数据库无匹配记录")
                except Exception as e:
                    print(f"Django数据库删除异常: {str(e)}")
                
                # 3. 返回响应
                # 无论删除是否成功，都返回成功，避免前端困惑
                print(f"删除结果 - MongoDB: {mongo_deleted}, Django: {django_deleted}")
                return JsonResponse({"Code": 0, "msg": "取消投递成功"})
            else:
                # 投递职位
                if not job_id:
                    return JsonResponse({"Code": 1, "msg": "职位ID不能为空"})
                    
                # 检查职位是否存在
                try:
                    job = db.job_datas.find_one({'_id': ObjectId(job_id)})
                    if not job:
                        return JsonResponse({"Code": 1, "msg": "职位不存在"})
                except Exception as e:
                    print(f"查询职位时出错: {str(e)}")
                    return JsonResponse({"Code": 1, "msg": "职位ID无效"})
                
                # 检查是否已经投递
                exists = db.send_list.find_one({
                    'user_id': user_id,
                    'job_id': job_id
                })
                if exists:
                    return JsonResponse({"Code": 1, "msg": "已经投递过该职位"})
                
                # 创建投递记录
                try:
                    now = datetime.now()
                    # 1. 先添加到MongoDB
                    record_data = {
                        'user_id': user_id,
                        'user_name': user.user_name,
                        'job_id': job_id,
                        'job_name': job.get('name', '未知职位'),
                        'company': job.get('company', '未知公司'),
                        'company_type': job.get('company_type', ''),
                        'company_size': job.get('company_size', ''),
                        'created_at': now
                    }
                    
                    mongo_result = db.send_list.insert_one(record_data)
                    print(f"MongoDB投递记录创建成功: {mongo_result.inserted_id}")
                    
                    # 2. 再添加到Django数据库
                    try:
                        django_record = models.SendList.objects.create(
                            user=user,
                            job_id=job_id,
                            job_name=job.get('name', '未知职位'),
                            company=job.get('company', '未知公司'),
                            company_type=job.get('company_type', ''),
                            company_size=job.get('company_size', ''),
                            created_at=now
                        )
                        print(f"Django数据库投递记录创建成功: ID={django_record.id}")
                    except Exception as e:
                        print(f"创建Django数据库记录时出错: {str(e)}")
                    
                    return JsonResponse({"Code": 0, "msg": "投递成功"})
                except Exception as e:
                    print(f"创建投递记录时出错: {str(e)}")
                    return JsonResponse({"Code": 1, "msg": "投递失败，请稍后重试"})
                    
        except Exception as e:
            print(f"Error in send_job: {str(e)}")
            return JsonResponse({"Code": 1, "msg": f"操作失败: {str(e)}"})
    
    return JsonResponse({"Code": 1, "msg": "不支持的请求方法"})


def job_expect(request):
    """此函数用于处理用户的求职期望"""
    if request.method == "POST":
        user_id = request.session.get("user_id")
        job_name = request.POST.get("key_word")
        city = request.POST.get("city")
        
        try:
            # 连接MongoDB
            db = get_mongodb()
            if not db:
                return JsonResponse({"Code": 1, "msg": "数据库连接失败"})
            
            # 更新或创建用户期望
            result = db.user_expect.update_one(
                {'user_id': user_id},
                {
                    '$set': {
                        'key_word': job_name,
                        'place': city,
                        'updated_at': datetime.now()
                    }
                },
                upsert=True
            )
            
            return JsonResponse({"Code": 0, "msg": "保存成功"})
            
        except Exception as e:
            print(f"Error in job_expect: {str(e)}")
            return JsonResponse({"Code": 1, "msg": "保存失败，请稍后重试"})
    else:
        try:
            # 连接MongoDB
            db = get_mongodb()
            if not db:
                return JsonResponse({"Code": 1, "msg": "数据库连接失败"})
            
            # 获取用户期望
            user_expect = db.user_expect.find_one({'user_id': request.session.get("user_id")})
            keyword = user_expect['key_word'] if user_expect else ''
            place = user_expect['place'] if user_expect else ''
            
            return render(request, "expect.html", locals())
            
        except Exception as e:
            print(f"Error in job_expect: {str(e)}")
            return render(request, "expect.html", {'keyword': '', 'place': ''})


def get_recommend(request):
    """获取职位推荐"""
    try:
        user_id = request.session.get("user_id")
        username = request.session.get("username")
        if not user_id and not username:
            return JsonResponse({"code": 1, "msg": "请先登录"})

        # 使用改进的推荐算法
        from job.job_recommend import recommend_by_item_id_mongo
        
        print(f"使用推荐算法为用户 {user_id or username} 生成职位推荐")
        recommended_jobs = recommend_by_item_id_mongo(user_id or username)
        
        if not recommended_jobs:
            # 如果算法没有返回推荐，使用原来的备用方法
            print("推荐算法未返回结果，使用备用方法")
            # 连接MongoDB
            db = get_mongodb()
            if not db:
                return JsonResponse({"code": 1, "msg": "MongoDB连接失败"})

            # 获取用户投递记录
            send_list = [str(record['job_id']) for record in db.send_list.find({'user_id': user_id})]
            
            # 获取用户期望
            user_expect = db.user_expect.find_one({'user_id': user_id})
            expect_job = user_expect['key_word'] if user_expect else None
            expect_city = user_expect['place'] if user_expect else None

            # 根据用户期望获取推荐职位，排除已投递的职位
            recommended_jobs = []
            if expect_job or expect_city:
                query = {}
                if expect_job:
                    query['name'] = {'$regex': expect_job, '$options': 'i'}
                if expect_city:
                    query['place'] = {'$regex': expect_city, '$options': 'i'}
                
                # 获取所有符合条件的职位
                all_jobs = list(db.job_datas.find(query))
                
                # 过滤掉已投递的职位
                recommended_jobs = [
                    job for job in all_jobs 
                    if str(job['_id']) not in send_list
                ][:9]

            # 如果推荐数量不足，添加其他未投递的职位
            if len(recommended_jobs) < 9:
                remaining = 9 - len(recommended_jobs)
                # 排除已推荐和已投递的职位ID
                existing_ids = {str(job['_id']) for job in recommended_jobs} | set(send_list)
                
                # 查询其他未投递的职位
                other_jobs = list(db.job_datas.find({
                    '_id': {'$nin': [ObjectId(id) for id in existing_ids]}
                }).limit(remaining))
                
                recommended_jobs.extend(other_jobs)
        
        # 获取用户投递记录，用于标记是否已投递
        db = get_mongodb()
        send_list = [str(record['job_id']) for record in db.send_list.find({'user_id': user_id})]
        
        # 处理ObjectId并添加投递状态
        for job in recommended_jobs:
            if isinstance(job.get('_id'), ObjectId):
                job['job_id'] = str(job['_id'])
                if 'job_id' not in job:
                    job['job_id'] = job['job_id']
            elif '_id' in job and 'job_id' not in job:
                job['job_id'] = str(job['_id'])
                
            job['is_sent'] = job['job_id'] in send_list
            
            # 确保移除原始ObjectId，避免序列化问题
            if '_id' in job and isinstance(job['_id'], ObjectId):
                del job['_id']

        return render(request, "recommend.html", {
            'recommend_list': recommended_jobs
        })

    except Exception as e:
        print(f"Error in get_recommend: {str(e)}")
        return JsonResponse({"code": 1, "msg": "获取推荐失败，请稍后重试"})


def send_page(request):
    return render(request, "send_list.html")


def send_list(request):
    """获取用户投递列表"""
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return JsonResponse({"code": 1, "msg": "请先登录", "count": 0, "data": []})

        # 连接MongoDB
        db = get_mongodb()
        if not db:
            return JsonResponse({"code": 1, "msg": "MongoDB连接失败", "count": 0, "data": []})

        # 获取用户的投递记录
        send_jobs = []
        for record in db.send_list.find({'user_id': user_id}).sort('created_at', -1):
            try:
                # 检查job_id是否有效
                if not record.get('job_id'):
                    print(f"无效的job_id记录: {record}")
                    continue

                # 尝试转换ObjectId
                try:
                    job_id = ObjectId(record['job_id'])
                except Exception as e:
                    print(f"无效的ObjectId格式: {record['job_id']}, 错误: {str(e)}")
                    # 删除无效记录
                    db.send_list.delete_one({'_id': record['_id']})
                    continue

                # 获取职位信息
                job = db.job_datas.find_one({'_id': job_id})
                if not job:
                    print(f"职位不存在: {record['job_id']}")
                    # 删除无效的投递记录
                    db.send_list.delete_one({'_id': record['_id']})
                    continue

                # 更新投递记录中的职位信息
                update_data = {
                    'job_name': job.get('name', '未知职位'),
                    'company': job.get('company', '未知公司'),
                    'company_type': job.get('company_type', '暂无数据'),
                    'company_size': job.get('company_size', '暂无数据')
                }
                db.send_list.update_one({'_id': record['_id']}, {'$set': update_data})

                # 构造返回数据
                job_data = {
                    '_id': str(job['_id']),  # 用于取消投递
                    'job_id': str(job['_id']),  # 保持兼容性
                    'name': job.get('name', '未知职位'),
                    'salary': job.get('salary', '薪资未知'),
                    'education': job.get('education', '要求未知'),
                    'experience': job.get('experience', '经验未知'),
                    'place': job.get('place', '地点未知'),
                    'company': job.get('company', '未知公司'),
                    'company_type': job.get('company_type', '暂无数据'),
                    'company_size': job.get('company_size', '暂无数据'),
                    'send_key': 1,
                    'created_at': record['created_at'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(record['created_at'], datetime) else str(record['created_at'])
                }
                send_jobs.append(job_data)

            except Exception as e:
                print(f"处理投递记录时出错: {str(e)}")
                continue

        return JsonResponse({
            "code": 0,
            "msg": "success" if send_jobs else "暂无投递记录",
            "count": len(send_jobs),
            "data": send_jobs
        })

    except Exception as e:
        print(f"Error in send_list: {str(e)}")
        return JsonResponse({
            "code": 1,
            "msg": f"获取投递列表失败: {str(e)}",
            "count": 0,
            "data": []
        })


def pass_page(request):
    user_obj = models.UserList.objects.filter(user_id=request.session.get("user_id")).first()
    return render(request, "pass_page.html", locals())


def up_info(request):
    if request.method == "POST":
        user_name = request.POST.get("user_name")
        old_pass = request.POST.get("old_pass")
        pass_word = request.POST.get("pass_word")
        user_obj = models.UserList.objects.filter(user_id=request.session.get("user_id")).first()
        if old_pass != user_obj.pass_word:
            return JsonResponse({"Code": 0, "msg": "原密码错误"})
        else:
            models.UserList.objects.filter(user_id=request.session.get("user_id")).update(user_name=user_name,
                                                                                          pass_word=pass_word)
            return JsonResponse({"Code": 0, "msg": "密码修改成功"})


def salary(request):
    return render(request, "salary.html")


def edu(request):
    return render(request, "edu.html")


def bar_page(request):
    return render(request, "bar_page.html")


def bar(request):
    """此函数用于获取职位关键字统计数据"""
    try:
        # 连接MongoDB
        db = get_mongodb()
        if not db:
            return JsonResponse({
                "Code": 1,
                "msg": "MongoDB连接失败",
                "bar_x": [],
                "bar_y": []
            })

        # 先检查是否有job_category字段，如果没有则运行分类脚本
        sample_job = db.job_datas.find_one({'job_category': {'$exists': True}})
        if not sample_job:
            # 导入并运行职位分类脚本
            from job.keyword_classifier import classify_job_keywords
            classify_job_keywords()

        # 统计职位分类
        pipeline = [
            {"$match": {"job_category": {"$exists": True}}},
            {"$group": {"_id": "$job_category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 12}  # 获取前12个分类
        ]
        
        categories = list(db.job_datas.aggregate(pipeline))
        
        if not categories:
            # 如果没有分类数据，回退到原来的关键词统计
            jobs = list(db.job_datas.find({}, {'key_word': 1}))
            
            if not jobs:
                return JsonResponse({
                    "Code": 1,
                    "msg": "暂无数据",
                    "bar_x": [],
                    "bar_y": []
                })
            
            # 统计关键词出现次数
            keyword_counter = {}
            for job in jobs:
                key_word = job.get('key_word', '')
                if key_word and isinstance(key_word, str):
                    # 移除空格并统计
                    key_word = key_word.strip()
                    if key_word:
                        keyword_counter[key_word] = keyword_counter.get(key_word, 0) + 1
            
            # 获取出现次数最多的12个关键词
            sorted_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)[:12]
            
            # 分离关键词和计数
            bar_x = [item[0] for item in sorted_keywords]
            bar_y = [int(item[1]) for item in sorted_keywords]
        else:
            # 使用职位分类统计
            bar_x = [item['_id'] for item in categories]
            bar_y = [int(item['count']) for item in categories]
        
        # 计算总职位数
        total_jobs = db.job_datas.count_documents({})
        total_keywords = sum(bar_y)
        
        return JsonResponse({
            "Code": 0,
            "msg": "success",
            "bar_x": bar_x,
            "bar_y": bar_y,
            "total_jobs": int(total_jobs),
            "total_keywords": int(total_keywords)
        })
        
    except Exception as e:
        print(f"Error in bar view: {str(e)}")
        return JsonResponse({
            "Code": 1,
            "msg": f"服务器错误: {str(e)}",
            "bar_x": [],
            "bar_y": []
        })


def get_salary_top10(request):
    """获取薪资最高的前10个职位"""
    try:
        # 连接MongoDB
        db = get_mongodb()
        if not db:
            return JsonResponse({'status': 'error', 'message': 'MongoDB连接失败'})

        # 从MongoDB获取所有职位数据
        job_data = list(db.job_datas.find())
        
        # 处理薪资数据
        for job in job_data:
            try:
                salary_str = job.get('salary', '')
                if not salary_str:
                    job['salary_value'] = 0
                    continue
                    
                # 处理多种可能的薪资格式
                if '-' in salary_str:  # 处理范围格式 (例如: "10k-20k")
                    max_salary = re.findall(r'(\d+)k', salary_str)
                    if len(max_salary) >= 2:  # 如果找到两个数字，取第二个作为最高薪资
                        salary_value = float(max_salary[1])
                    elif len(max_salary) == 1:  # 如果只找到一个数字
                        salary_value = float(max_salary[0])
                    else:
                        salary_value = 0
                else:  # 处理单个数值格式 (例如: "20k")
                    salary_match = re.findall(r'(\d+)k', salary_str)
                    salary_value = float(salary_match[0]) if salary_match else 0
                
                job['salary_value'] = salary_value
                
            except Exception as e:
                print(f"Error processing salary for job {job.get('_id', 'unknown')}: {str(e)}")
                job['salary_value'] = 0
        
        # 按薪资排序并获取前10
        sorted_jobs = sorted(job_data, key=lambda x: x.get('salary_value', 0), reverse=True)[:10]
        
        # 构造返回数据
        result = []
        for job in sorted_jobs:
            # 处理公司名称，确保显示合适长度
            company_name = job.get('company', '未知')
            if len(company_name) > 20:  # 如果公司名称过长，截取前20个字符
                company_name = company_name[:17] + '...'
                
            # 获取公司行业和规模信息
            company_type = job.get('company_type', '行业未知')
            company_size = job.get('company_size', '规模未知')
            
            result.append({
                '_id': str(job['_id']),  # 添加职位编号
                'name': job.get('name', '未知'),
                'company': company_name,
                'salary': job.get('salary', '未知'),
                'place': job.get('place', '未知'),
                'education': job.get('education', '未知'),
                'experience': job.get('experience', '未知'),
                'company_type': company_type,  # 公司行业
                'company_size': company_size  # 公司规模
            })
            
        return JsonResponse({
            'code': 0,  # layui table 需要这个状态码
            'msg': '',
            'count': len(result),
            'data': result
        })
        
    except Exception as e:
        print(f"Error in get_salary_top10 view: {e}")
        return JsonResponse({
            'code': 1,
            'msg': str(e),
            'count': 0,
            'data': []
        })

# 新增视图函数
def word_cloud_page(request):
    """显示关键词词云页面"""
    return render(request, "word_cloud.html")

def get_word_cloud_data(request):
    """提供词云数据接口"""
    try:
        print("开始获取词云数据...")
        # 连接MongoDB
        db = get_mongodb()
        if not db:
            print("MongoDB连接失败")
            return JsonResponse({'code': 1, 'msg': 'MongoDB连接失败', 'data': []})

        # 获取所有职位数据
        job_data = list(db.job_datas.find({}, {'name': 1, 'company_type': 1, 'description': 1}))
        print(f"从MongoDB获取到{len(job_data)}条职位数据")
        
        if not job_data:
            print("未获取到有效职位数据")
            return JsonResponse({'code': 1, 'msg': '未获取到有效职位数据', 'data': []})
        
        # 导入jieba分词
        import jieba
        
        # 提取所有职位名称中的关键词
        keywords = []
        for job in job_data:
            # 处理职位名称
            if 'name' in job and job['name']:
                # 使用jieba进行中文分词
                job_name = job['name']
                print(f"处理职位名称: {job_name}")
                words = jieba.lcut(job_name)
                for word in words:
                    if len(word) > 1 and not word.isdigit():  # 过滤数字和单字符
                        keywords.append(word)
                        
                # 提取职位名称中的关键词
                job_keywords = extract_job_keywords(job['name'])
                for keyword in job_keywords:
                    if keyword and len(keyword) > 1:  # 过滤掉空字符串和单字符
                        keywords.append(keyword)
            
            # 处理公司类型
            if 'company_type' in job and job['company_type']:
                company_type = job['company_type'].replace('/', '').replace('-', '').strip()
                if company_type and len(company_type) > 1:
                    words = jieba.lcut(company_type)
                    for word in words:
                        if len(word) > 1 and not word.isdigit():
                            keywords.append(word)
        
        print(f"提取出的关键词总数: {len(keywords)}")
        if not keywords:
            print("未提取到有效关键词")
            # 返回一些测试数据
            test_data = [
                {'name': '测试数据1', 'value': 100},
                {'name': '测试数据2', 'value': 80},
                {'name': '测试数据3', 'value': 60},
                {'name': '测试数据4', 'value': 40},
                {'name': '测试数据5', 'value': 20}
            ]
            return JsonResponse({
                'code': 0,
                'msg': 'success (test data)',
                'data': test_data
            })
        
        # 统计关键词频率
        keyword_counter = Counter(keywords)
        
        # 转换为词云所需的格式
        word_cloud_data = [
            {'name': word, 'value': count}
            for word, count in keyword_counter.most_common(100)  # 取频率最高的100个词
            if len(word) > 1  # 确保关键词长度大于1
        ]
        
        print(f"生成词云数据: {len(word_cloud_data)}个关键词")
        print(f"前10个关键词: {word_cloud_data[:10]}")
        
        return JsonResponse({
            'code': 0,
            'msg': 'success',
            'data': word_cloud_data
        })
        
    except Exception as e:
        print(f"Error in get_word_cloud_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'code': 1, 'msg': str(e), 'data': []})

def geo_distribution_page(request):
    """显示地理位置分布页面"""
    return render(request, "geo_distribution.html")

def get_geo_distribution_data(request):
    """提供地理位置分布数据接口"""
    try:
        print("开始获取地理分布数据...")
        # 连接MongoDB
        db = get_mongodb()
        if not db:
            print("MongoDB连接失败")
            return JsonResponse({'code': 1, 'msg': 'MongoDB连接失败', 'data': []})

        # 从所有职位中提取地点信息
        pipeline = [
            {"$group": {"_id": "$place", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 50}  # 获取职位数量最多的50个地区
        ]
        
        locations = list(db.job_datas.aggregate(pipeline))
        print(f"获取到{len(locations)}个地点信息")
        
        if not locations:
            print("未获取到有效地点数据，提供测试数据")
            # 提供测试数据
            test_data = [
                {'name': '北京', 'value': 100, 'coords': [116.407526, 39.90403]},
                {'name': '上海', 'value': 80, 'coords': [121.473701, 31.230416]},
                {'name': '广州', 'value': 60, 'coords': [113.264434, 23.129162]},
                {'name': '深圳', 'value': 50, 'coords': [114.057868, 22.543099]},
                {'name': '杭州', 'value': 40, 'coords': [120.209947, 30.246071]}
            ]
            return JsonResponse({
                'code': 0,
                'msg': 'success (test data)',
                'data': test_data
            })
        
        # 城市到地理坐标的映射
        city_coordinates = {
            '北京': [116.407526, 39.90403],
            '上海': [121.473701, 31.230416],
            '广州': [113.264434, 23.129162],
            '深圳': [114.057868, 22.543099],
            '杭州': [120.209947, 30.246071],
            '成都': [104.065735, 30.659462],
            '南京': [118.796877, 32.060255],
            '武汉': [114.305392, 30.593099],
            '西安': [108.948024, 34.263161],
            '重庆': [106.551556, 29.563009],
            '苏州': [120.585294, 31.298886],
            '天津': [117.190186, 39.125595],
            '长沙': [112.938814, 28.228209],
            '郑州': [113.625368, 34.746599],
            '东莞': [113.751799, 23.020673],
            '宁波': [121.55069, 29.873859],
            '佛山': [113.121416, 23.021548],
            '青岛': [120.382639, 36.067082],
            '沈阳': [123.431474, 41.805698],
            '济南': [117.12, 36.651216],
            '厦门': [118.089478, 24.479509],
            '福州': [119.306236, 26.075302],
            '无锡': [120.311914, 31.491169],
            '大连': [121.614682, 38.914003],
            '合肥': [117.227239, 31.820586],
            '昆明': [102.832891, 24.880095],
            '哈尔滨': [126.534967, 45.803775],
            '长春': [125.3245, 43.886841],
            '南宁': [108.320007, 22.82402],
            '常州': [119.974061, 31.811226],
            '中山': [113.392782, 22.517646],
            '石家庄': [114.513986, 38.042306],
            '贵阳': [106.630153, 26.647661],
            '南昌': [115.858197, 28.682892],
            '太原': [112.548879, 37.87059],
            '惠州': [114.416196, 23.111847]
        }
        
        # 处理地点数据
        geo_data = []
        for loc in locations:
            city_name = loc['_id']
            if not city_name:
                continue
                
            # 提取城市名称（通常格式为"城市-区域"或"城市"）
            city = city_name.split('-')[0].split('·')[0].strip()
            
            # 查找城市坐标
            coords = city_coordinates.get(city)
            if coords:
                geo_data.append({
                    'name': city,
                    'value': loc['count'],
                    'coords': coords
                })
            else:
                print(f"未找到城市 {city} 的坐标")
        
        print(f"生成地理数据: {len(geo_data)}个城市")
        if len(geo_data) > 0:
            print(f"前5个城市数据: {geo_data[:5]}")
        
        if not geo_data:
            print("未生成有效地理数据，提供测试数据")
            # 提供测试数据
            test_data = [
                {'name': '北京', 'value': 100, 'coords': [116.407526, 39.90403]},
                {'name': '上海', 'value': 80, 'coords': [121.473701, 31.230416]},
                {'name': '广州', 'value': 60, 'coords': [113.264434, 23.129162]},
                {'name': '深圳', 'value': 50, 'coords': [114.057868, 22.543099]},
                {'name': '杭州', 'value': 40, 'coords': [120.209947, 30.246071]}
            ]
            return JsonResponse({
                'code': 0,
                'msg': 'success (test data)',
                'data': test_data
            })
        
        return JsonResponse({
            'code': 0,
            'msg': 'success',
            'data': geo_data
        })
        
    except Exception as e:
        print(f"Error in get_geo_distribution: {str(e)}")
        import traceback
        traceback.print_exc()
        # 提供测试数据
        test_data = [
            {'name': '北京', 'value': 100, 'coords': [116.407526, 39.90403]},
            {'name': '上海', 'value': 80, 'coords': [121.473701, 31.230416]},
            {'name': '广州', 'value': 60, 'coords': [113.264434, 23.129162]},
            {'name': '深圳', 'value': 50, 'coords': [114.057868, 22.543099]},
            {'name': '杭州', 'value': 40, 'coords': [120.209947, 30.246071]}
        ]
        return JsonResponse({
            'code': 0,
            'msg': 'success (test data)',
            'data': test_data
        })

def company_scale_page(request):
    """显示公司规模分布页面"""
    return render(request, "company_scale.html")

def get_company_scale_data(request):
    """提供公司规模分布数据接口"""
    try:
        print("开始获取公司规模数据...")
        # 连接MongoDB
        db = get_mongodb()
        if not db:
            print("MongoDB连接失败")
            return JsonResponse({
                'code': 0,
                'msg': 'MongoDB连接失败 (test data)',
                'labels': ['小型企业', '中型企业', '大型企业', '初创企业', '其他'],
                'values': [40, 30, 20, 5, 5]
            })

        # 从所有职位中提取公司规模信息
        pipeline = [
            {"$group": {"_id": "$company_size", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        company_sizes = list(db.job_datas.aggregate(pipeline))
        print(f"获取到{len(company_sizes)}个公司规模类型")
        
        if not company_sizes:
            print("未获取到有效公司规模数据，提供测试数据")
            return JsonResponse({
                'code': 0,
                'msg': 'success (test data)',
                'labels': ['小型企业', '中型企业', '大型企业', '初创企业', '其他'],
                'values': [40, 30, 20, 5, 5]
            })
        
        # 规模分类映射
        size_mapping = {
            '少于50人': '初创企业',
            '50-150人': '小型企业', 
            '150-500人': '小型企业',
            '500-1000人': '中型企业',
            '1000-2000人': '中型企业',
            '2000-5000人': '大型企业',
            '5000-10000人': '大型企业',
            '10000人以上': '大型企业'
        }
        
        # 合并规模数据
        scale_counter = defaultdict(int)
        for item in company_sizes:
            size = item['_id']
            print(f"处理公司规模: {size}")
            if not size:
                scale_counter['其他'] += item['count']
                continue
            
            # 映射到标准规模分类
            category = '其他'
            for key, value in size_mapping.items():
                if key in size:
                    category = value
                    break
            
            scale_counter[category] += item['count']
        
        # 准备图表数据
        labels = list(scale_counter.keys())
        values = [scale_counter[key] for key in labels]
        
        print(f"生成公司规模数据: {len(labels)}个类别")
        print(f"类别: {labels}")
        print(f"数值: {values}")
        
        if not labels or not values:
            print("未生成有效数据，提供测试数据")
            return JsonResponse({
                'code': 0,
                'msg': 'success (test data)',
                'labels': ['小型企业', '中型企业', '大型企业', '初创企业', '其他'],
                'values': [40, 30, 20, 5, 5]
            })
        
        return JsonResponse({
            'code': 0,
            'msg': 'success',
            'labels': labels,
            'values': values
        })
        
    except Exception as e:
        print(f"Error in get_company_scale_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'code': 0,
            'msg': 'error (test data)',
            'labels': ['小型企业', '中型企业', '大型企业', '初创企业', '其他'],
            'values': [40, 30, 20, 5, 5]
        })

def experience_analysis_page(request):
    """显示工作经验分析页面"""
    return render(request, "experience_analysis.html")

def get_experience_data(request):
    """提供工作经验分析数据接口"""
    try:
        print("开始获取工作经验数据...")
        # 连接MongoDB
        db = get_mongodb()
        if not db:
            print("MongoDB连接失败")
            return JsonResponse({
                'code': 0,
                'msg': 'MongoDB连接失败 (test data)',
                'labels': ['1-3年', '3-5年', '5-10年', '不限', '应届毕业生', '1年以下', '10年以上'],
                'values': [35, 25, 15, 10, 8, 5, 2]
            })

        # 从所有职位中提取工作经验要求
        pipeline = [
            {"$group": {"_id": "$experience", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        experiences = list(db.job_datas.aggregate(pipeline))
        print(f"获取到{len(experiences)}个工作经验类型")
        
        if not experiences:
            print("未获取到有效工作经验数据，提供测试数据")
            return JsonResponse({
                'code': 0,
                'msg': 'success (test data)',
                'labels': ['1-3年', '3-5年', '5-10年', '不限', '应届毕业生', '1年以下', '10年以上'],
                'values': [35, 25, 15, 10, 8, 5, 2]
            })
        
        # 经验分类
        exp_categories = {
            '应届毕业生': 0,
            '1年以下': 0,
            '1-3年': 0,
            '3-5年': 0,
            '5-10年': 0,
            '10年以上': 0,
            '不限': 0,
            '其他': 0
        }
        
        # 处理经验数据
        for item in experiences:
            exp = item['_id']
            count = item['count']
            
            if not exp:
                exp_categories['其他'] += count
                continue
            
            print(f"处理工作经验: {exp} (数量: {count})")    
            matched = False
            for category in exp_categories.keys():
                if category in exp:
                    exp_categories[category] += count
                    matched = True
                    break
            
            if not matched:
                exp_categories['其他'] += count
        
        # 准备图表数据
        labels = [key for key, value in exp_categories.items() if value > 0]
        values = [value for key, value in exp_categories.items() if value > 0]
        
        print(f"生成工作经验数据: {len(labels)}个类别")
        print(f"类别: {labels}")
        print(f"数值: {values}")
        
        if not labels or not values:
            print("未生成有效数据，提供测试数据")
            return JsonResponse({
                'code': 0,
                'msg': 'success (test data)',
                'labels': ['1-3年', '3-5年', '5-10年', '不限', '应届毕业生', '1年以下', '10年以上'],
                'values': [35, 25, 15, 10, 8, 5, 2]
            })
        
        return JsonResponse({
            'code': 0,
            'msg': 'success',
            'labels': labels,
            'values': values
        })
        
    except Exception as e:
        print(f"Error in get_experience_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'code': 0,
            'msg': 'error (test data)',
            'labels': ['1-3年', '3-5年', '5-10年', '不限', '应届毕业生', '1年以下', '10年以上'],
            'values': [35, 25, 15, 10, 8, 5, 2]
        })
