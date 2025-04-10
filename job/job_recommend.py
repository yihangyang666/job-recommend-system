#!/usr/bin/python3.9.10
# -*- coding: utf-8 -*-
# @Time    : 2023/2/18 9:41
# @File    : job_recommend.py
import os
import sys
import django
from math import sqrt
import random
from pymongo import MongoClient
from bson.objectid import ObjectId

# 添加项目根目录到Python路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# MongoDB连接函数
def get_mongodb():
    """获取MongoDB连接"""
    try:
        # 尝试从Django配置获取连接信息
        try:
            # 设置Django设置模块
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "JobRecommend.settings")
            django.setup()
            from django.conf import settings
            mongo_uri = getattr(settings, 'MONGO_URI', 'mongodb://localhost:27017/')
            mongo_db = getattr(settings, 'MONGO_DB', 'job_recommend_db')  # 使用正确的数据库名
        except Exception as e:
            print(f"无法从Django设置获取MongoDB配置: {e}")
            # 使用正确的数据库名和凭据
            mongo_uri = 'mongodb://localhost:27017/'
            mongo_db = 'job_recommend_db'
        
        # 连接MongoDB
        client = MongoClient(mongo_uri)
        db = client[mongo_db]
        print(f"成功连接到MongoDB数据库: {mongo_db}")
        return db
    except Exception as e:
        print(f"MongoDB连接失败: {e}")
        return None


# 计算相似度 - 使用MongoDB
def similarity_mongo(job1_id, job2_id, db):
    """
    计算两个职位之间的相似度，基于共同投递用户
    使用余弦相似度: common / sqrt(job1_sum * job2_sum)
    
    Args:
        job1_id: 第一个职位ID
        job2_id: 第二个职位ID
        db: MongoDB数据库连接
        
    Returns:
        float: 相似度分数，范围0-1
    """
    # 获取投递job1的用户
    job1_users = set(
        str(send['user_id']) for send in db.send_list.find({'job_id': job1_id})
    )
    
    # 获取投递job2的用户
    job2_users = set(
        str(send['user_id']) for send in db.send_list.find({'job_id': job2_id})
    )
    
    # 两者的交集
    common_users = job1_users.intersection(job2_users)
    
    # 计算相似度
    job1_count = len(job1_users)
    job2_count = len(job2_users)
    
    # 没有人投递当前职位
    if job1_count == 0 or job2_count == 0:
        return 0
    
    similar_value = len(common_users) / sqrt(job1_count * job2_count)  # 余弦计算相似度
    return similar_value


# 基于物品的推荐算法 - 使用MongoDB
def recommend_by_item_id_mongo(user_id, k=9):
    """
    基于物品的协同过滤推荐算法，直接使用MongoDB
    
    Args:
        user_id: 用户ID (可以是字符串ID、用户名或ObjectId)
        k: 推荐结果数量，默认9个
        
    Returns:
        list: 推荐的职位列表
    """
    print(f"为用户 {user_id} 生成推荐...")
    
    # 连接MongoDB
    db = get_mongodb()
    if not db:
        print("MongoDB连接失败")
        return []
    
    # 检查用户是否存在 - 支持多种ID格式
    user = None
    
    # 尝试不同的查询方式
    if ObjectId.is_valid(user_id):
        user = db.user_list.find_one({"_id": ObjectId(user_id)})
    
    # 如果按ID找不到，尝试按用户名查找
    if not user:
        user = db.user_list.find_one({"username": user_id})
    
    # 如果还找不到，尝试按user_id字段查找
    if not user:
        user = db.user_list.find_one({"user_id": user_id})
    
    if not user:
        print(f"用户 {user_id} 不存在")
        return []
    
    # 获取实际用户ID
    actual_user_id = str(user.get('_id'))
    print(f"找到用户，实际ID: {actual_user_id}")
    
    # 获取用户最新的求职意向
    user_expect = db.user_expect.find_one({"user_id": actual_user_id}) or db.user_expect.find_one({"user_id": user_id})
    
    # 获取用户投递记录
    send_records = list(db.send_list.find({"user_id": actual_user_id}))
    
    # 如果没有找到投递记录，尝试使用原始用户ID查询
    if not send_records:
        send_records = list(db.send_list.find({"user_id": user_id}))
    
    # 如果用户没有投递记录但有求职意向，使用意向推荐
    if not send_records and user_expect:
        print(f"用户没有投递记录，使用求职意向推荐: {user_expect.get('key_word', '')}")
        query = {}
        if user_expect.get('key_word'):
            query['name'] = {'$regex': user_expect['key_word'], '$options': 'i'}
        if user_expect.get('place'):
            query['place'] = {'$regex': user_expect['place'], '$options': 'i'}
        
        # 获取符合条件的职位
        job_list = list(db.job_datas.find(query))
        
        if len(job_list) > k:
            job_list = random.sample(job_list, k)  # 随机k个推荐
        
        print(f"基于用户意向推荐了 {len(job_list)} 个职位")
        
        # 为每个职位添加job_id字段
        for job in job_list:
            job['job_id'] = str(job['_id'])
            
        return job_list
    
    # 同时考虑历史投递和最新意向
    # 1. 从历史投递中获取关键词偏好
    sent_job_ids = [record['job_id'] for record in send_records]
    sent_jobs = []
    key_word_list = []
    
    for job_id in sent_job_ids:
        try:
            job = db.job_datas.find_one({"_id": ObjectId(job_id)})
            if job:
                sent_jobs.append(job)
                if 'key_word' in job:
                    key_word_list.append(job['key_word'])
        except Exception as e:
            print(f"获取职位详情出错: {e}")
            continue
    
    # 统计关键词频率并选取偏好关键词
    user_prefer = []
    if key_word_list:
        key_word_list_unique = list(set(key_word_list))
        for key_word in key_word_list_unique:
            user_prefer.append([key_word, key_word_list.count(key_word)])
        
        user_prefer = sorted(user_prefer, key=lambda x: x[1], reverse=True)  # 排序
        user_prefer = [x[0] for x in user_prefer[0:2]]  # 找出最多的2个关键词
        
    # 2. 将最新的求职意向加入偏好列表（优先考虑）
    if user_expect and user_expect.get('key_word'):
        # 将最新的求职意向放在偏好列表最前面
        if user_expect['key_word'] in user_prefer:
            # 如果已经在列表中，移到最前面
            user_prefer.remove(user_expect['key_word'])
            user_prefer.insert(0, user_expect['key_word'])
        else:
            # 如果不在列表中，直接添加到最前面
            user_prefer.insert(0, user_expect['key_word'])
    
    # 如果没有任何关键词偏好，随机推荐
    if not user_prefer:
        print("无法获取用户关键词偏好，返回随机推荐")
        job_list = list(db.job_datas.find({"_id": {"$nin": [ObjectId(jid) for jid in sent_job_ids]}}).limit(100))
        
        if len(job_list) > k:
            job_list = random.sample(job_list, k)
        
        # 为每个职位添加job_id字段
        for job in job_list:
            job['job_id'] = str(job['_id'])
            
        return job_list
    
    print(f"用户偏好关键词 (包含最新意向): {user_prefer}")
    
    # 获取未投递过且包含偏好关键词的职位
    # 对不同的关键词分别进行查询并分配权重
    all_jobs = []
    
    # 根据最新意向推荐60%
    if user_expect and user_expect.get('key_word') and user_expect['key_word'] in user_prefer:
        primary_keyword = user_expect['key_word']
        primary_count = int(k * 0.6)  # 60%的推荐基于最新意向
        
        pipeline = [
            {"$match": {
                "_id": {"$nin": [ObjectId(jid) for jid in sent_job_ids]},
                "$or": [
                    {"name": {"$regex": primary_keyword, "$options": "i"}},
                    {"key_word": primary_keyword}
                ]
            }},
            {"$sample": {"size": primary_count}}
        ]
        
        primary_jobs = list(db.job_datas.aggregate(pipeline))
        all_jobs.extend(primary_jobs)
        
        # 已获取的职位ID
        existing_ids = set(job['_id'] for job in all_jobs) | set(ObjectId(jid) for jid in sent_job_ids)
        
        # 获取其他偏好关键词的职位
        remaining_count = k - len(all_jobs)
        if remaining_count > 0 and len(user_prefer) > 1:
            remaining_keywords = [kw for kw in user_prefer if kw != primary_keyword]
            
            pipeline = [
                {"$match": {
                    "_id": {"$nin": list(existing_ids)},
                    "$or": [
                        {"key_word": {"$in": remaining_keywords}},
                        {"name": {"$regex": "|".join(remaining_keywords), "$options": "i"}}
                    ]
                }},
                {"$sample": {"size": remaining_count}}
            ]
            
            secondary_jobs = list(db.job_datas.aggregate(pipeline))
            all_jobs.extend(secondary_jobs)
    else:
        # 如果没有最新意向，则均匀分配不同关键词的权重
        for i, keyword in enumerate(user_prefer):
            count = max(1, int(k / len(user_prefer)))
            existing_ids = set(job['_id'] for job in all_jobs) | set(ObjectId(jid) for jid in sent_job_ids)
            
            pipeline = [
                {"$match": {
                    "_id": {"$nin": list(existing_ids)},
                    "$or": [
                        {"key_word": keyword},
                        {"name": {"$regex": keyword, "$options": "i"}}
                    ]
                }},
                {"$sample": {"size": count}}
            ]
            
            keyword_jobs = list(db.job_datas.aggregate(pipeline))
            all_jobs.extend(keyword_jobs)
    
    # 如果推荐不足k个，从未投递职位中随机补充
    if len(all_jobs) < k:
        print(f"推荐不足 {k} 个，从未投递职位中随机补充")
        remaining = k - len(all_jobs)
        
        existing_ids = set(job['_id'] for job in all_jobs) | set(ObjectId(jid) for jid in sent_job_ids)
        
        pipeline = [
            {"$match": {"_id": {"$nin": list(existing_ids)}}},
            {"$sample": {"size": remaining}}
        ]
        
        extra_jobs = list(db.job_datas.aggregate(pipeline))
        all_jobs.extend(extra_jobs)
    
    # 确保不超过k个
    if len(all_jobs) > k:
        all_jobs = all_jobs[:k]
    
    # 为每个职位添加job_id字段
    for job in all_jobs:
        job['job_id'] = str(job['_id'])
    
    print(f"成功生成 {len(all_jobs)} 个推荐")
    return all_jobs


# 用于测试的主函数
if __name__ == '__main__':
    # 测试推荐算法
    try:
        # 尝试多个可能的用户ID格式，包括用户名、ObjectId和字符串
        test_ids = [
            "lmfy",  # 用户名
            "测试_1",
            "测试_2", 
            "67d2d3e631755a34736b5d90",  # 尝试使用截图中的ObjectId格式
            "67d2d3e631755a34736b5d91",
            "67d2d3e631755a34736b5d92"
        ]
        
        for test_user_id in test_ids:
            print(f"\n尝试为用户 {test_user_id} 生成推荐...")
            try:
                results = recommend_by_item_id_mongo(test_user_id)
                if results:
                    print(f"为用户 {test_user_id} 推荐了 {len(results)} 个职位:")
                    for i, job in enumerate(results[:3]):  # 只显示前3个结果
                        print(f"{i+1}. {job.get('name', '未知职位')} - {job.get('company', '未知公司')}")
                    if len(results) > 3:
                        print(f"... 还有 {len(results)-3} 个推荐结果")
                    break  # 找到有效用户后退出
            except Exception as e:
                print(f"为用户 {test_user_id} 生成推荐时出错: {str(e)}")
                continue
        else:
            print("\n未找到有效用户，请确认数据库中存在用户数据")
            
            # 检查数据库中的用户集合
            db = get_mongodb()
            if db:
                collections = db.list_collection_names()
                print(f"\n数据库中的集合: {collections}")
                
                # 检查用户集合
                if 'user_list' in collections:
                    users = list(db.user_list.find().limit(5))
                    print(f"\n用户集合中的前5条记录:")
                    for user in users:
                        print(f"用户ID: {user.get('_id')}, 用户名: {user.get('username', '未知')}")
                
                # 尝试查找名为 lmfy 的用户
                lmfy_user = db.user_list.find_one({"username": "lmfy"})
                if lmfy_user:
                    print(f"\n找到用户 lmfy: {lmfy_user}")
                    print(f"尝试为 lmfy 用户生成推荐...")
                    results = recommend_by_item_id_mongo(str(lmfy_user['_id']))
                    if results:
                        print(f"为用户 lmfy 推荐了 {len(results)} 个职位")
                        for i, job in enumerate(results[:3]):
                            print(f"{i+1}. {job.get('name', '未知职位')} - {job.get('company', '未知公司')}")
                else:
                    print("\n未找到用户 lmfy")
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
