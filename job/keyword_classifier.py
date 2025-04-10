from pymongo import MongoClient
from django.conf import settings
import re
import sys

def get_job_category(keyword):
    """根据职位关键词判断职位类别"""
    # 首先检查是否是实习生
    if any(k in keyword for k in ['实习生', '实习', '见习']):
        return '实习生'
        
    # 后端开发类别关键词
    backend_keywords = ['java', 'python', 'php', 'golang', 'go', '后端', '服务端', 'node.js', '.net', 'c#']
    if any(k in keyword.lower() for k in backend_keywords):
        return '后端开发'
    
    # C++开发类别
    cpp_keywords = ['c++', 'cpp', 'c语言']
    if any(k in keyword.lower() for k in cpp_keywords):
        return 'C++开发'
    
    # 前端开发类别
    frontend_keywords = ['前端', 'javascript', 'js', 'html', 'css', 'vue', 'react', 'angular']
    if any(k in keyword.lower() for k in frontend_keywords):
        return '前端开发'
    
    # 人工智能类别
    ai_keywords = ['人工智能', '机器学习', '深度学习', 'nlp', '自然语言处理', '计算机视觉', 'cv', '图像识别', '算法', 'ai', 'ml']
    if any(k in keyword.lower() for k in ai_keywords):
        return '人工智能'
    
    # 数据分析类别
    data_keywords = ['数据分析', '数据挖掘', '商业分析', 'bi', '数据可视化', '统计分析', '数据库', 'sql', 'nosql']
    if any(k in keyword.lower() for k in data_keywords):
        return '数据分析'
    
    # 运维/测试类别
    ops_test_keywords = ['运维', '测试', 'devops', 'sre', 'qa', '质量', '系统管理', '网络管理']
    if any(k in keyword.lower() for k in ops_test_keywords):
        return '运维/测试'
    
    # UI/UX设计类别
    design_keywords = ['ui', 'ux', '用户体验', '交互设计', '视觉设计', '平面设计', '设计师']
    if any(k in keyword.lower() for k in design_keywords):
        return 'UI/UX设计'
    
    # 嵌入式/硬件类别
    embedded_keywords = ['嵌入式', '单片机', 'arm', '硬件', 'fpga', 'vhdl', 'pcb']
    if any(k in keyword.lower() for k in embedded_keywords):
        return '嵌入式/硬件'
    
    # 云计算/架构类别
    cloud_keywords = ['云计算', '云原生', 'kubernetes', 'k8s', 'docker', '微服务', '架构师', '分布式']
    if any(k in keyword.lower() for k in cloud_keywords):
        return '云计算/架构'
    
    # 自动驾驶类别
    auto_drive_keywords = ['自动驾驶', '无人驾驶', '无人车', '智能驾驶', '智能汽车', '计算机视觉']
    if any(k in keyword.lower() for k in auto_drive_keywords):
        return '自动驾驶'
    
    # 行业研究类别
    research_keywords = ['研究', '调研', '行业分析', '策略研究', '咨询']
    if any(k in keyword.lower() for k in research_keywords):
        return '行业研究'
    
    # 产品经理类别
    pm_keywords = ['产品经理', 'pm', '产品运营', '需求分析']
    if any(k in keyword.lower() for k in pm_keywords):
        return '产品经理'
    
    # 如果没有匹配到任何类别，则返回更广泛的匹配
    if '开发' in keyword or '工程师' in keyword:
        return '软件开发'
    
    # 默认返回其他
    return '其他职位'


def classify_job_keywords():
    """将职位关键词分类并更新到MongoDB"""
    try:
        # 连接MongoDB
        client = MongoClient(settings.MONGODB_URI)
        db = client[settings.MONGODB_NAME]
        print(f"成功连接到MongoDB: {settings.MONGODB_URI}")
        
        # 获取所有职位数据
        jobs = list(db.job_datas.find())
        print(f"获取到 {len(jobs)} 条职位数据")
        
        # 记录每个类别的数量
        category_counts = {}
        
        # 为每个职位分配类别
        for job in jobs:
            job_title = job.get('name', '')
            job_category = get_job_category(job_title)
            
            # 更新职位分类
            db.job_datas.update_one(
                {'_id': job['_id']},
                {'$set': {'job_category': job_category}}
            )
            
            # 统计分类结果
            category_counts[job_category] = category_counts.get(job_category, 0) + 1
        
        # 打印分类结果
        print("职位分类结果:")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"{category}: {count}")
        
        print(f"总共处理了 {len(jobs)} 条职位数据")
        return True
        
    except Exception as e:
        print(f"职位分类失败: {str(e)}")
        return False


if __name__ == "__main__":
    # 如果是直接运行此文件
    print("开始运行职位分类器...")
    result = classify_job_keywords()
    sys.exit(0 if result else 1) 