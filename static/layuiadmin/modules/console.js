/** layuiAdmin.std-v1.0.0 LPPL License By http://www.layui.com/admin/ */ ;
layui.define(function(e) {
	layui.use(["admin", "carousel"], function() {
		var e = layui.$,
			t = (layui.admin, layui.carousel),
			a = layui.element,
			i = layui.device();
		e(".layadmin-carousel").each(function() {
			var a = e(this);
			t.render({
				elem: this,
				width: "100%",
				arrow: "none",
				interval: a.data("interval"),
				autoplay: a.data("autoplay") === !0,
				trigger: i.ios || i.android ? "click" : "hover",
				anim: a.data("anim")
			})
		}), a.render("progress")
	}), layui.use(["carousel", "echarts"], function() {
		var e = layui.$,
			$ = layui.jquery,
			layer = layui.layer,
			a = (layui.carousel, layui.echarts),
			l = [],
			t = [{
				title: {
					text: "学历分布和薪资分布",
					x: "center",
					textStyle: {
						fontSize: 14
					}
				},
				tooltip: {
					trigger: "item",
					formatter: "{a} <br/>{b} : {c} ({d}%)"
				},
				series: [{
					name: "学历要求",
					type: "pie",
					radius: "70%",
					center: ["25%", "50%"],
					data: []
				},{
					name: "薪资待遇",
					type: "pie",
					radius: "70%",
					center: ["75%", "50%"],
					data: []
				}]
			}],
			i = e("#LAY-index-dataview").children("div"),
			n = function(e) {
				l[e] = a.init(i[e], layui.echartsTheme);
				l[e].setOption(t[e]);
				window.onresize = l[e].resize;
			};

		// 获取数据并渲染图表
		var loadData = function() {
			$.ajax({
				type: 'GET',
				url: '/get_pie/',
				success: function(res) {
					if (!res.edu_data || !res.salary_data) {
						layer.msg('获取数据失败');
						return;
					}
					t[0].series[0].data = res.edu_data;
					t[0].series[1].data = res.salary_data;
					i[0] && n(0);
				},
				error: function(response) {
					layer.msg('服务器错误，请稍后重试');
				}
			});
		};

		// 立即加载数据
		loadData();

		// 每60秒刷新一次数据
		setInterval(loadData, 60000);

	}), layui.use(["carousel", "echarts"], function() {
		var e = layui.$,
			$ = layui.jquery,
			layer = layui.layer,
			a = (layui.carousel, layui.echarts),
			l = [],
			t = [{
				series: [
					{
						name: 'Pressure',
						type: 'gauge',
						radius: '70%',
						axisLine: {
							lineStyle: {
								width: 4
							}
						},
						center: ['25%', '50%'],
						progress: {
							show: true
						},
						detail: {
							valueAnimation: true,
							formatter: '{value}%',
							textStyle:{
								fontSize:20
							}
						},
						data: [
							{
								value: 0,
								name: 'CPU使用率'
							}
						],
						splitLine:{
							lineStyle:{
								width: 1
							}
						},
						title:{
							offsetCenter : [0, '30%']
						}
					},
					{
						name: 'Pressure',
						type: 'gauge',
						radius: '70%',
						axisLine: {
							lineStyle: {
								width: 4
							}
						},
						center: ['75%', '50%'],
						progress: {
							show: true
						},
						detail: {
							valueAnimation: true,
							formatter: '{value}%',
							textStyle:{
								fontSize:20
							}
						},
						data: [
							{
								value: 0,
								name: '内存使用率'
							}
						],
						splitLine:{
							lineStyle:{
								width: 1
							}
						},
						title:{
							offsetCenter : [0, '30%']
						}
					}
				]
			}],
			i = e("#LAY-index-control").children("div"),
			n = function(e) {
				l[e] = a.init(i[e], layui.echartsTheme);
				l[e].setOption(t[e]);
				window.onresize = l[e].resize;
			};

		i[0] && n(0);

		// 定时更新系统监控数据
		var updateMonitor = function() {
			$.ajax({
				type: 'GET',
				url: '/get_psutil/',
				success: function(res) {
					if (!res.cpu_data || !res.memory_data) {
						layer.msg('获取系统数据失败');
						return;
					}
					t[0].series[0].data[0].value = (res.cpu_data).toFixed(2) - 0;
					t[0].series[1].data[0].value = (res.memory_data).toFixed(2) - 0;
					l[0].setOption(t[0]);
				},
				error: function(response) {
					layer.msg('服务器错误，请稍后重试');
				}
			});
		};

		// 立即执行一次更新
		updateMonitor();
		
		// 每30秒更新一次
		setInterval(updateMonitor, 30000);
	}), layui.use("table", function() {
		var e = (layui.$, layui.table);
		e.render({
			elem: "#LAY-index-topSearch",
			url: layui.setter.base + "json/console/top-search.js",
			page: !0,
			cols: [
				[{
					type: "numbers",
					fixed: "left"
				}, {
					field: "keywords",
					title: "关键词",
					minWidth: 300,
					templet: '<div><a href="https://www.baidu.com/s?wd={{ d.keywords }}" target="_blank" class="layui-table-link">{{ d.keywords }}</div>'
				}, {
					field: "frequency",
					title: "搜索次数",
					minWidth: 120,
					sort: !0
				}, {
					field: "userNums",
					title: "用户数",
					sort: !0
				}]
			],
			skin: "line"
		}), e.render({
			elem: "#LAY-index-topCard",
			url: layui.setter.base + "json/console/top-card.js",
			page: !0,
			cellMinWidth: 120,
			cols: [
				[{
					type: "numbers",
					fixed: "left"
				}, {
					field: "title",
					title: "标题",
					minWidth: 300,
					templet: '<div><a href="{{ d.href }}" target="_blank" class="layui-table-link">{{ d.title }}</div>'
				}, {
					field: "username",
					title: "发帖者"
				}, {
					field: "channel",
					title: "类别"
				}, {
					field: "crt",
					title: "点击率",
					sort: !0
				}]
			],
			skin: "line"
		})
	}), e("console", {})
});