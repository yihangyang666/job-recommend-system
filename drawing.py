from pymongo import MongoClient
from pyecharts.charts import Pie, Gauge, Line, HeatMap
from pyecharts import options as opts
import random

# 连接MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['job_recommend_db']
collection = db['job_datas']

# 创建饼图
pie = Pie()
pie.add(
    "学历分布",
    [("博士", 5), ("硕士", 20), ("本科", 60), ("大专", 15)],
    radius=["30%", "75%"],
    center=["25%", "50%"],
    rosetype="radius"
)
pie.set_global_opts(title_opts=opts.TitleOpts(title="学历分布和薪资分布"))

# 创建仪表盘
gauge = Gauge()
gauge.add(
    "系统监控",
    [("CPU使用率", 16.7), ("内存使用率", 83.1)]
)
gauge.set_global_opts(title_opts=opts.TitleOpts(title="系统监控"))

# 创建折线图
line = Line()
line.add_xaxis(["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
line.add_yaxis("访问量", [random.randint(100, 200) for _ in range(7)])
line.set_global_opts(title_opts=opts.TitleOpts(title="网站访问量"))

# 创建热力图
heatmap = HeatMap()
hours = ["12a", "1a", "2a", "3a", "4a", "5a", "6a", "7a", "8a", "9a", "10a", "11a",
         "12p", "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p", "10p", "11p"]
days = ["Saturday", "Friday", "Thursday", "Wednesday", "Tuesday", "Monday", "Sunday"]
data = [[i, j, random.randint(0, 100)] for i in range(24) for j in range(7)]
heatmap.add_xaxis(hours)
heatmap.add_yaxis("", days, data)
heatmap.set_global_opts(
    title_opts=opts.TitleOpts(title="热力图示例"),
    visualmap_opts=opts.VisualMapOpts()
)

# 渲染图表
pie.render("pie_chart.html")
gauge.render("gauge_chart.html")
line.render("line_chart.html")
heatmap.render("heatmap_chart.html") 