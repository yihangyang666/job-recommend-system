from django.shortcuts import render, redirect
from django.http import JsonResponse
# Create your views here.
from job import models
import re
from psutil import *
from numpy import *
from job import tools
from job import job_recommend
from collections import Counter

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
        user = request.POST.get('user')
        pass_word = request.POST.get('password')
        print('user------>', user)
        users_list = list(models.UserList.objects.all().values("user_id"))
        users_id = [x['user_id'] for x in users_list]
        print(users_id)
        # print(students_num)
        ret = models.UserList.objects.filter(user_id=user, pass_word=pass_word)
        if user not in users_id:
            return JsonResponse({'code': 1, 'msg': '该账号不存在！'})
        elif ret:
            # 有此用户 -->> 跳转到首页
            # 登录成功后，将用户名和昵称保存到session 中，
            request.session['user_id'] = user
            user_obj = ret.last()

            if user_obj:  # 检查用户对象是否存在
                user_name = user_obj.user_name
                request.session['user_name'] = user_name
                return JsonResponse({'code': 0, 'msg': '登录成功！', 'user_name': user_name})
        else:
            return JsonResponse({'code': 1, 'msg': '密码错误！'})
    else:
        return render(request, "login.html")


def register(request):
    if request.method == "POST":
        user = request.POST.get('user')
        pass_word = request.POST.get('password')
        user_name = request.POST.get('user_name')
        users_list = list(models.UserList.objects.all().values("user_id"))
        users_id = [x['user_id'] for x in users_list]
        if user in users_id:
            return JsonResponse({'code': 1, 'msg': '该账号已存在！'})
        else:
            models.UserList.objects.create(user_id=user, user_name=user_name, pass_word=pass_word)
            request.session['user_id'] = user  # 设置缓存
            request.session['user_name'] = user_name
            return JsonResponse({'code': 0, 'msg': '注册成功！'})
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


def welcome(request):
    """此函数用于处理控制台页面"""
    try:
        # 查询所有的职位信息
        job_data = list(models.JobData.objects.all().values())
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
                salary_str = job['salary']
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
                print(f"Error processing salary for job {job.get('job_id', 'unknown')}: {str(e)}")
                job['salary_1'] = 0
                list_1.append(0)
                
        # 反向排序所有职位信息的最高薪资
        job_data = sorted(job_data, key=lambda x: x['salary_1'], reverse=True)
        job_data_10 = job_data[0:10]  # 取最高薪资前10用来渲染top-10表格
        job_data_1 = job_data[0]  # 取出最高薪资的职位信息
        mean_salary = int(mean(list_1)) if list_1 else 0  # 计算平均薪资
        
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
        spider_code = 1  # 改变爬虫状态
        spider_model = models.SpiderInfo.objects.filter(spider_id=1).first()
        # print(spider_model)
        spider_model.count += 1  # 给次数+1
        spider_model.page += int(page)  # 给爬取页数加上选择的页数
        spider_model.save()
        if role == '猎聘网':
            # print(key_word,city,page)
            spider_code = tools.lieSpider(key_word=key_word, city=city, all_page=page)
        return JsonResponse({"code": 0, "msg": "爬取完毕!"})
    else:
        return JsonResponse({"code": 1, "msg": "请使用POST请求"})


def job_list(request):
    return render(request, "job_list.html", locals())


def get_job_list(request):
    """此函数用来渲染职位信息列表"""
    page = int(request.GET.get("page", ""))  # 获取请求地址中页码
    limit = int(request.GET.get("limit", ""))  # 获取请求地址中的每页数据数量
    keyword = request.GET.get("keyword", "")
    price_min = request.GET.get("price_min", "")
    price_max = request.GET.get("price_max", "")
    edu = request.GET.get("edu", "")
    city = request.GET.get("city", "")
    job_data_list = list(models.JobData.objects.filter(name__icontains=keyword, education__icontains=edu,
                                                       place__icontains=city).values())  # 查询所有的职位信息
    job_data = []
    if price_min != "" or price_max != "":
        for job in job_data_list:
            try:
                salary_1 = '薪资' + job['salary']
                max_salary = float(re.findall(r'-(\d+)k', salary_1)[0])  # 使用正则提取最高薪资
                min_salary = float(re.findall(r'薪资(\d+)', salary_1)[0])  # 使用正则提取最低薪资
                if price_min == "" and price_max != "":
                    if max_salary <= float(price_max):
                        job_data.append(job)
                elif price_min != "" and price_max == "":
                    if min_salary >= float(price_min):
                        job_data.append(job)
                else:
                    if min_salary >= float(price_min) and float(price_max) >= max_salary:
                        job_data.append(job)
            except Exception as e:  # 如果筛选不出就跳过
                continue
    else:
        job_data = job_data_list
    job_data_1 = job_data[(page - 1) * limit:limit * page]
    for job in job_data_1:
        ret = models.SendList.objects.filter(user_id=request.session.get("user_id"), job_id=job['job_id']).values()
        if ret:
            job['send_key'] = 1
        else:
            job['send_key'] = 0
    # print(job_data_1)
    if len(job_data) == 0 or len(job_data_list) == 0:
        return JsonResponse({"code": 1, "msg": "没找到需要查询的数据！", "count": "{}".format(len(job_data)), "data": job_data_1})
    return JsonResponse({"code": 0, "msg": "success", "count": "{}".format(len(job_data)), "data": job_data_1})


def get_psutil(request):
    """此函数用于读取cpu使用率和内存占用率"""
    # cpu_percent()可以获取cpu的使用率，参数interval是获取的间隔
    # virtual_memory()[2]可以获取内存的使用率
    return JsonResponse({'cpu_data': cpu_percent(interval=1), 'memory_data': virtual_memory()[2]})


def get_pie(request):
    """此函数用于渲染控制台饼图的数据,要求学历的数据和薪资待遇的数据"""
    try:
        # 查询所有的职位信息
        job_data = list(models.JobData.objects.all().values())
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
            edu_count = len([job for job in job_data if edu in job['education']])
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
                salary_str = job['salary']
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
                print(f"Error processing salary for job {job.get('job_id', 'unknown')}: {str(e)}")
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
        job_id = request.POST.get("job_id")
        send_key = request.POST.get("send_key")
        if int(send_key) == 1:
            models.SendList.objects.filter(user_id=user_id, job_id=job_id).delete()
        else:
            models.SendList.objects.create(user_id=user_id, job_id=job_id)
        return JsonResponse({"Code": 0, "msg": "操作成功"})


def job_expect(request):
    if request.method == "POST":
        job_name = request.POST.get("key_word")
        city = request.POST.get("city")
        ret = models.UserExpect.objects.filter(user=request.session.get("user_id"))
        # print(ret)
        if ret:
            ret.update(key_word=job_name, place=city)
        else:
            user_obj = models.UserList.objects.filter(user_id=request.session.get("user_id")).first()
            models.UserExpect.objects.create(user=user_obj, key_word=job_name, place=city)
        return JsonResponse({"Code": 0, "msg": "操作成功"})
    else:
        ret = models.UserExpect.objects.filter(user=request.session.get("user_id")).values()
        print(ret)
        if len(ret) != 0:
            keyword = ret[0]['key_word']
            place = ret[0]['place']
        else:
            keyword = ''
            place = ''
        return render(request, "expect.html", locals())


def get_recommend(request):
    """获取职位推荐"""
    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({"code": 1, "msg": "请先登录"})
    try:
        recommend_list = job_recommend.recommend_by_item_id(user_id, 9)
        return render(request, "recommend.html", locals())
    except Exception as e:
        print(f"Error in get_recommend: {str(e)}")
        return JsonResponse({"code": 1, "msg": "获取推荐失败，请稍后重试"})


def send_page(request):
    return render(request, "send_list.html")


def send_list(request):
    send_list = list(models.JobData.objects.filter(sendlist__user=request.session.get("user_id")).values())
    for send in send_list:
        send['send_key'] = 1
    if len(send_list) == 0:
        return JsonResponse({"code": 1, "msg": "没找到需要查询的数据！", "count": "{}".format(len(send_list)), "data": []})
    else:
        return JsonResponse({"code": 0, "msg": "success", "count": "{}".format(len(send_list)), "data": send_list})


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
        # 从数据库获取最新数据，并转换为列表格式
        jobs = list(models.JobData.objects.values_list('name', flat=True))
        job_data = [name for name in jobs if name]  # 过滤掉空值
        
        if not job_data:
            return JsonResponse({
                "Code": 1,
                "msg": "暂无数据",
                "bar_x": [],
                "bar_y": []
            })
        
        # 使用新的动态关键词提取逻辑
        keyword_counter = Counter()
        
        for job_name in job_data:
            keywords = extract_job_keywords(job_name)
            # 只统计非空的关键词
            valid_keywords = [k for k in keywords if k and k.strip()]
            if valid_keywords:  # 只有当提取到有效关键词时才计数
                keyword_counter.update(valid_keywords)
        
        if not keyword_counter:
            return JsonResponse({
                "Code": 1,
                "msg": "暂无关键词数据",
                "bar_x": [],
                "bar_y": []
            })
        
        # 获取出现次数最多的12个关键词
        top_keywords = keyword_counter.most_common(12)
        
        # 确保数据是基本类型，并且只包含非空的关键词
        bar_x = [str(item[0]) for item in top_keywords if item[0]]  # 转换为字符串列表，排除空值
        bar_y = [int(item[1]) for item in top_keywords if item[0]]  # 确保是Python原生int类型，排除空值对应的计数
        
        # 计算总职位数和关键词总数（确保是Python原生int类型）
        total_jobs = int(len(job_data))
        total_keywords = int(sum(bar_y))
        
        print("Debug info:")
        print(f"Keywords found: {len(keyword_counter)}")
        print(f"Top keywords: {top_keywords[:3]}")
        print(f"Bar X: {bar_x}")
        print(f"Bar Y: {bar_y}")
        print(f"Total jobs: {total_jobs}")
        print(f"Total keywords: {total_keywords}")
        
        # 构造响应数据
        response_data = {
            "Code": 0,
            "msg": "success",
            "bar_x": bar_x,
            "bar_y": bar_y,
            "total_jobs": total_jobs,
            "total_keywords": total_keywords
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Error in bar view: {str(e)}")
        print(f"Error location: {e.__traceback__.tb_lineno}")
        print(f"Error type: {type(e)}")
        return JsonResponse({
            "Code": 1,
            "msg": f"服务器错误: {str(e)}",
            "bar_x": [],
            "bar_y": []
        })
