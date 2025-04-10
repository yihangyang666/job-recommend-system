# 职位推荐系统

这是一个基于Django和MongoDB的职位推荐系统，提供职位搜索、推荐、数据分析等功能。

## 功能特点

- 用户认证系统（登录/注册）
- 职位搜索和筛选
  - 按关键词搜索
  - 按薪资范围筛选
  - 按学历要求筛选
  - 按工作地点筛选
- 职位推荐
  - 基于用户兴趣的个性化推荐
  - 智能职位匹配
- 数据分析和可视化
  - 薪资分布分析
  - 学历要求分析
  - 职位关键词分析
  - CPU和内存使用监控
- 职位数据爬虫
  - 支持猎聘网数据采集
  - 可配置关键词和城市
  - 可设置采集页数

## 技术栈

- 后端框架：Django
- 数据库：MongoDB (使用djongo作为ORM)
- 前端框架：LayUI
- 数据分析：NumPy
- 系统监控：psutil
- 数据可视化：ECharts

## 安装说明

1. 克隆项目
```bash
git clone [repository-url]
cd job-recommend-system
```

2. 创建并激活虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置MongoDB
- 确保MongoDB服务已启动
- 默认连接地址：mongodb://localhost:27017/
- 数据库名：job_recommend_db

5. 运行数据库迁移
```bash
python manage.py makemigrations
python manage.py migrate
```

6. 启动服务器
```bash
python manage.py runserver
```

## 项目结构

```
job-recommend-system/
├── JobRecommend/          # 项目配置目录
├── job/                   # 主应用目录
│   ├── models.py         # 数据模型
│   ├── views.py          # 视图函数
│   ├── tools.py          # 工具函数
│   └── job_recommend.py  # 推荐算法
├── static/               # 静态文件
├── templates/            # 模板文件
├── manage.py            # Django管理脚本
├── requirements.txt     # 项目依赖
└── README.md           # 项目文档
```

## 数据模型

- UserList：用户信息
- JobData：职位信息
- UserInterest：用户兴趣
- SendList：投递记录
- UserExpect：用户期望
- SpiderInfo：爬虫信息

## API接口

### 用户相关
- POST /login/ - 用户登录
- POST /register/ - 用户注册
- GET /logout/ - 用户登出

### 职位相关
- GET /job_list/ - 获取职位列表
- POST /send_job/ - 投递/取消投递职位
- GET /get_recommend/ - 获取推荐职位

### 数据分析
- GET /get_pie/ - 获取饼图数据（学历和薪资分布）
- GET /get_psutil/ - 获取系统资源使用情况
- GET /bar/ - 获取职位关键词统计

### 爬虫相关
- POST /start_spider/ - 启动爬虫任务

## 使用说明

1. 用户注册/登录
2. 设置职位期望（关键词和城市）
3. 浏览职位列表，可使用多个筛选条件
4. 查看推荐职位
5. 投递感兴趣的职位
6. 查看数据分析图表

## 注意事项

- 确保MongoDB服务正常运行
- 爬虫使用需遵守目标网站的robots协议
- 建议在虚拟环境中运行项目
- 生产环境部署时需修改相关安全设置

## 贡献指南

1. Fork 项目
2. 创建特性分支 (git checkout -b feature/AmazingFeature)
3. 提交更改 (git commit -m 'Add some AmazingFeature')
4. 推送到分支 (git push origin feature/AmazingFeature)
5. 创建Pull Request

## 许可证

[MIT License](LICENSE) 