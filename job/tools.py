import time
from lxml import etree
from multiprocessing.dummy import Pool
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import requests
import random
import pyecharts
import urllib.parse

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 指定 chromedriver 的路径
driver_path = os.path.join(current_dir, 'chromedriver.exe')


def get_mongodb():
    """连接MongoDB数据库"""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client['job_recommend_db']

        # 确保所需的集合都存在
        if 'job_datas' not in db.list_collection_names():
            db.create_collection('job_datas')
            db.job_datas.create_index(
                [('name', 1), ('company', 1), ('href', 1)], unique=True)
            print('创建 job_datas 集合')
        else:
            print(f'job_datas集合已存在，当前文档数: {db.job_datas.count_documents({})}')

        if 'send_list' not in db.list_collection_names():
            db.create_collection('send_list')
            db.send_list.create_index(
                [('user_id', 1), ('job_id', 1)], unique=True)
            print('创建 send_list 集合')

        if 'user_expect' not in db.list_collection_names():
            db.create_collection('user_expect')
            db.user_expect.create_index([('user_id', 1)], unique=True)
            print('创建 user_expect 集合')

        print('MongoDB连接成功')
        return db
    except Exception as e:
        print(f'MongoDB连接失败: {str(e)}')
        return None


def lieSpider(key_word, city, all_page):
    """猎聘网爬虫主函数"""
    city_dict = {'全国': '410', '北京': '010', '上海': '020', '天津': '030', '重庆': '040', '广州': '050020',
                 '深圳': '050090', '苏州': '060080', '南京': '060020', '杭州': '070020', '大连': '210040',
                 '成都': '280020', '武汉': '170020', '西安': '270020'}

    print(f'开始爬取猎聘网 {city} {key_word}的职位信息...')
    urls_list = get_urls(key_word, all_page, city_dict[city])
    pool = Pool(1)  # 线程池对象，速度过快封IP，只能开一个线程
    pool.map(get_pages, urls_list)
    return 0


def get_urls(key_word, all_page, city_code):
    """生成猎聘网需要爬取的数据的URL"""
    urls_list = []
    for i in range(0, int(all_page)):
        url = f'https://www.liepin.com/zhaopin/?city={city_code}&dq={city_code}&currentPage={i}&pageSize=40&key={key_word}'
        urls_list.append(url)
    return urls_list


def get_pages(url):
    """爬取猎聘网页面职位信息并保存到MongoDB"""
    print(f'开始爬取 {url}...')

    # 连接MongoDB
    db = get_mongodb()
    if not db:
        print('MongoDB连接失败，无法保存数据')
        return

    try:
        # 配置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # 获取页面数据
        driver.get(url)
        time.sleep(3)
        req_html = etree.HTML(driver.page_source)

        # 提取数据
        name = req_html.xpath(
            '//div[@class="jsx-2387891236 ellipsis-1"]/text()')
        salary = req_html.xpath(
            '//span[@class="jsx-2387891236 job-salary"]/text()')
        address = req_html.xpath(
            '//span[@class="jsx-2387891236 ellipsis-1"]/text()')

        # 获取职位标签盒子，然后分别提取学历和经验
        job_labels_boxes = req_html.xpath(
            '//div[@class="jsx-2387891236 job-labels-box"]')
        education = []
        experience = []

        for box in job_labels_boxes:
            spans = box.xpath('./span/text()')
            edu_found = False
            exp_found = False

            # 遍历所有标签，识别哪个是学历，哪个是经验
            for span_text in spans:
                # 学历标识词：学历、本科、硕士、博士、大专、高中、初中、学位等
                if any(keyword in span_text for keyword in [
                       '本科', '硕士', '博士', '大专', '学历', '学位', '高中', '中专', '初中']):
                    education.append(span_text)
                    edu_found = True
                # 经验标识词：经验、实习、应届、年、月等
                elif any(keyword in span_text for keyword in ['经验', '应届', '年', '以上']):
                    experience.append(span_text)
                    exp_found = True
                # 处理特殊情况：如果包含"个月"、"天/周"这类字符串，通常是指实习时长，不是学历
                elif '个月' in span_text or '天/周' in span_text:
                    if '实习' not in experience:  # 确保不重复添加
                        experience.append('实习')
                    exp_found = True
                # 如果直接包含"实习"字样，归为经验类别
                elif '实习' in span_text:
                    experience.append(span_text)
                    exp_found = True

            # 如果没找到对应标签，添加默认值
            if not edu_found:
                # 对于实习岗位，如果没找到学历但找到了实习相关标签，默认设置为"本科"
                if any('实习' in exp for exp in experience):
                    education.append('本科')
                else:
                    education.append('学历不限')
            if not exp_found:
                experience.append('经验不限')

        company = req_html.xpath(
            '//span[@class="jsx-2387891236 company-name ellipsis-1"]/text()')

        # 处理公司标签和规模
        company_tags = req_html.xpath(
            '//div[@class="jsx-2387891236 company-tags-box ellipsis-1"]')
        label_list = []
        scale_list = []

        for tag in company_tags:
            # 获取所有标签
            all_spans = tag.xpath('.//span/text()')
            if all_spans:
                # 处理公司行业标签（通常是第一个标签）
                industry = all_spans[0] if all_spans else ''

                # 处理公司规模（通常包含"人"字的标签）
                scale = ''
                for span in all_spans:
                    if '人' in span:
                        scale = span
                        break

                # 如果没有找到包含"人"的标签，使用最后一个标签作为规模
                if not scale and len(all_spans) > 1:
                    scale = all_spans[-1]

                label_list.append(industry)
                scale_list.append(scale if scale else '规模未知')
            else:
                label_list.append('行业未知')
                scale_list.append('规模未知')

        # 处理职位链接
        href_list = req_html.xpath(
            '//a[@data-nick="job-detail-job-info"]/@href')
        href_list = [x.split('?')[0] for x in href_list]

        # 检查并确保数据一致性
        max_len = max(
            len(name),
            len(salary),
            len(address),
            len(company),
            len(job_labels_boxes),
            len(href_list))

        # 如果列表长度不一致，扩展较短的列表
        if len(label_list) < max_len:
            label_list.extend(['行业未知'] * (max_len - len(label_list)))
        if len(scale_list) < max_len:
            scale_list.extend(['规模未知'] * (max_len - len(scale_list)))

        print(f"找到 {len(name)} 个职位，整理后数据长度：{max_len}")

        # 使用有效长度保存职位数据
        valid_count = min(
            len(name),
            len(salary),
            len(address),
            len(company),
            len(href_list))
        saved_count = 0

        for i in range(valid_count):
            try:
                # 检查职位是否已存在
                existing_job = db.job_datas.find_one({
                    'name': name[i],
                    'company': company[i],
                    'href': href_list[i]
                })

                if not existing_job:
                    # 处理公司名称，确保完整性
                    company_name = company[i].strip()
                    if len(company_name) > 50:  # 如果公司名称过长，截取前50个字符
                        company_name = company_name[:47] + '...'

                    # 确保有有效的教育和经验数据
                    edu = education[i] if i < len(education) else '学历不限'
                    exp = experience[i] if i < len(experience) else '经验不限'

                    job_data = {
                        '_id': ObjectId(),
                        'name': name[i],
                        'salary': salary[i],
                        'place': address[i],
                        'education': edu,
                        'experience': exp,
                        'company': company_name,
                        'company_type': label_list[i] if i < len(label_list) else '行业未知',
                        'company_size': scale_list[i] if i < len(scale_list) else '规模未知',
                        # 使用公司行业作为标签
                        'label': label_list[i] if i < len(label_list) else '行业未知',
                        'href': href_list[i],
                        'key_word': url.split('=')[-1],
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    }

                    try:
                        # 插入数据到MongoDB中的job_datas集合
                        result = db.job_datas.insert_one(job_data)
                        saved_count += 1
                        print(
                            f'成功保存职位: {name[i]} - {company_name} ({job_data["company_type"]}, {job_data["company_size"]}), ID: {result.inserted_id}')
                        print(f'  学历要求: {edu}, 经验要求: {exp}')
                    except Exception as e:
                        print(f'保存职位失败 {name[i]}: {str(e)}')
                else:
                    print(f'职位已存在，跳过: {name[i]} - {company[i]}')
            except Exception as e:
                print(f'处理职位数据失败: {str(e)}')
                continue

        print(f'本次成功保存 {saved_count} 个新职位')

        time.sleep(3)
        driver.quit()

    except Exception as e:
        print(f'爬取页面失败: {str(e)}')
    finally:
        if 'driver' in locals():
            driver.quit()


def get_city():
    """获取猎聘网城市列表"""
    print('开始抓取猎聘网城市列表...')

    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        city_url = 'https://www.liepin.com/zhaopin/?inputFrom=head_navigation&scene=init&workYearCode=0'
        driver.get(city_url)
        time.sleep(3)

        req_html = etree.HTML(driver.page_source)
        code_list = req_html.xpath('//li[@data-key="dq"]/@data-code')
        name_list = req_html.xpath('//li[@data-key="dq"]/@data-name')
        city_list = [[name_list[x], code_list[x]]
                     for x in range(len(name_list))]

        print('抓取到的城市列表:', city_list)
        return city_list

    except Exception as e:
        print(f'获取城市列表失败: {str(e)}')
        return []
    finally:
        if 'driver' in locals():
            driver.quit()

# 以下是新增的51job网站爬虫功能


def job51Spider(city, key_word):
    """51job爬虫主函数"""
    # 连接MongoDB
    db = get_mongodb()
    if not db:
        print('MongoDB连接失败，无法进行爬取')
        return None

    try:
        # 获取城市代码
        city_dict = {'全国': '000000', '北京': '010000', '上海': '020000', '天津': '030000', '重庆': '040000',
                     '广州': '030200', '深圳': '040000', '苏州': '070300', '南京': '070200', '杭州': '080200',
                     '大连': '230300', '成都': '090200', '武汉': '180200', '西安': '200200'}

        if city not in city_dict:
            print(f'不支持的城市: {city}')
            return None

        city_code = city_dict[city]
        print(f'开始爬取51job {city}({city_code}) {key_word}的职位信息...')

        # 获取所有页面URL
        urls_list = get_51job_urls(key_word, city_code)

        # 使用进程池爬取
        pool = Pool(1)  # 线程池对象，速度过快封IP，只能开一个线程
        pool.map(get_51job_pages, urls_list)
        pool.close()
        pool.join()

        print(f'51job爬虫任务完成: {city} - {key_word}')
        return 0

    except Exception as e:
        print(f'爬取51job失败: {str(e)}')
        return 1
    finally:
        if 'driver' in locals():
            driver.quit()


def get_51job_urls(keyword, city):
    """获取51job的职位链接列表"""
    urls_list = []

    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # 获取总页数
        first_page_url = f'https://search.51job.com/list/{city},000000,0000,00,9,99,{keyword},2,1.html'
        driver.get(first_page_url)
        time.sleep(3)

        # 获取总页数
        total_page = 30  # 默认最多爬取30页

        # 生成所有页面的URL
        for page in range(1, total_page + 1):
            page_url = f'https://search.51job.com/list/{city},000000,0000,00,9,99,{keyword},2,{page}.html'
            urls_list.append(page_url)

        print(f'获取到 {len(urls_list)} 个页面URL')
        return urls_list

    except Exception as e:
        print(f'获取51job职位链接失败: {str(e)}')
        return urls_list
    finally:
        if 'driver' in locals():
            driver.quit()


def get_51job_pages(url):
    """爬取51job页面职位信息并保存到MongoDB"""
    print(f'开始爬取51job: {url}...')

    # 连接MongoDB
    db = get_mongodb()
    if not db:
        print('MongoDB连接失败，无法保存数据')
        return

    try:
        # 配置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        # 添加随机User-Agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
        ]
        chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # 获取页面数据
        driver.get(url)
        time.sleep(5)  # 51job可能需要更长的加载时间
        req_html = etree.HTML(driver.page_source)

        # 提取数据 - 51job的XPath选择器
        job_items = req_html.xpath('//div[@class="j_joblist"]/div[@class="e"]')

        if not job_items:
            print('未找到职位列表，尝试使用备用选择器')
            # 尝试备用选择器
            job_items = req_html.xpath(
                '//div[contains(@class, "j_joblist")]/div[contains(@class, "e")]')

            if not job_items:
                print(f'无法在{url}中找到职位列表，请检查网页结构或XPath选择器')
                driver.save_screenshot('51job_debug.png')
                print(f'已保存页面截图到 51job_debug.png')
                return

        print(f'找到 {len(job_items)} 个职位条目')
        saved_count = 0

        for item in job_items:
            try:
                # 提取职位名称
                name_elem = item.xpath('.//p[@class="t"]/span/a')
                if not name_elem:
                    continue
                name = name_elem[0].text.strip() if name_elem[0].text else ''

                # 提取职位链接
                href = name_elem[0].get('href', '')

                # 提取薪资
                salary_elem = item.xpath(
                    './/p[@class="info"]/span[@class="sal"]')
                salary = salary_elem[0].text.strip(
                ) if salary_elem and salary_elem[0].text else '薪资面议'

                # 提取地点
                address_elem = item.xpath(
                    './/p[@class="info"]/span[@class="d at"]')
                address = address_elem[0].text.strip(
                ) if address_elem and address_elem[0].text else '地点未知'

                # 提取公司名称
                company_elem = item.xpath('.//div[@class="er"]/a')
                company = company_elem[0].text.strip(
                ) if company_elem and company_elem[0].text else '公司未知'

                # 提取公司类型和规模
                company_info_elem = item.xpath('.//p[@class="dc at"]')
                company_info = company_info_elem[0].text.strip(
                ) if company_info_elem and company_info_elem[0].text else ''

                company_type = '行业未知'
                company_size = '规模未知'
                if company_info:
                    info_parts = company_info.split('|')
                    company_type = info_parts[0].strip() if len(
                        info_parts) > 0 else '行业未知'
                    company_size = info_parts[-1].strip() if len(
                        info_parts) > 1 else '规模未知'

                # 提取学历和经验要求
                job_info_elem = item.xpath('.//p[@class="tags"]/span')
                job_info = [span.text.strip()
                            for span in job_info_elem if span.text]

                education = '学历不限'
                experience = '经验不限'

                for info in job_info:
                    # 学历关键词
                    if any(keyword in info for keyword in [
                           '本科', '硕士', '博士', '大专', '学历', '学位']):
                        education = info
                    # 经验关键词
                    elif any(keyword in info for keyword in ['经验', '年', '应届']):
                        experience = info

                # 检查职位是否已存在
                existing_job = db.job_datas.find_one({
                    'name': name,
                    'company': company,
                    'href': href
                })

                if not existing_job and name and company:
                    # 处理公司名称，确保完整性
                    company_name = company.strip()
                    if len(company_name) > 50:  # 如果公司名称过长，截取前50个字符
                        company_name = company_name[:47] + '...'

                    # 构造并保存职位数据
                    job_data = {
                        'name': name,
                        'company': company_name,
                        'salary': salary,
                        'address': address,
                        'education': education,
                        'experience': experience,
                        'company_type': company_type,
                        'company_size': company_size,
                        'href': href,
                        'source': '51job',
                        'create_time': datetime.now()
                    }

                    # 保存到MongoDB
                    db.job_datas.insert_one(job_data)
                    saved_count += 1
                    print(f'成功保存职位: {name} - {company_name}')

            except Exception as e:
                print(f'处理职位数据时出错: {str(e)}')
                continue

        print(f'本页面成功保存 {saved_count} 个职位')

    except Exception as e:
        print(f'爬取页面失败: {str(e)}')
    finally:
        if 'driver' in locals():
            driver.quit()


def get_51job_city(city):
    """获取51job的城市代码"""
    # 连接MongoDB
    db = get_mongodb()
    if not db:
        print('MongoDB连接失败，无法获取城市代码')
        return None

    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        city_url = f'https://search.51job.com/list/{city},000000,0000,00,9,99,python,2,1.html'
        driver.get(city_url)
        time.sleep(3)

        req_html = etree.HTML(driver.page_source)
        city_elements = req_html.xpath('//div[@class="el city"]//a')

        city_list = []
        for element in city_elements:
            city_name = element.text.strip()
            city_code = element.get('href', '').split('/')[4].split(',')[0]
            if city_name and city_code:
                city_list.append([city_name, city_code])

        print('抓取到的51job城市列表:', city_list)
        return city_list

    except Exception as e:
        print(f'获取51job城市列表失败: {str(e)}')
        return []
    finally:
        if 'driver' in locals():
            driver.quit()


def get_city_code():
    """获取猎聘网城市代码列表"""
    # 连接MongoDB
    db = get_mongodb()
    if not db:
        print('MongoDB连接失败，无法获取城市代码')
        return []

    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        city_url = 'https://www.liepin.com/zhaopin/?inputFrom=head_navigation&scene=init&workYearCode=0'
        driver.get(city_url)
        time.sleep(3)

        req_html = etree.HTML(driver.page_source)
        code_list = req_html.xpath('//li[@data-key="dq"]/@data-code')
        name_list = req_html.xpath('//li[@data-key="dq"]/@data-name')
        city_list = [[name_list[x], code_list[x]]
                     for x in range(len(name_list))]

        print('抓取到的城市列表:', city_list)
        return city_list

    except Exception as e:
        print(f'获取城市列表失败: {str(e)}')
        return []
    finally:
        if 'driver' in locals():
            driver.quit()


if __name__ == '__main__':
    # 测试爬虫
    # lieSpider('python', '北京', '1')
    # job51Spider('python', '北京')
    pass
