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
					text: "职位关键字-柱形图",
					subtext: "职位数量"
				},
				tooltip: {
					trigger: "axis"
				},
				legend: {
					data: ["职位数量"]
				},
				xAxis: [{
					type: "category",
					data: []
				}],
				yAxis: [{
					type: "value",
					name: "数量"
				}],
				series: [{
					name: "职位数量",
					type: "bar",
					barWidth: 50,
					data: [],
					itemStyle: {
						normal: {
							label: {
								show: true,
								position: 'top',
								textStyle: {
									color: 'black',
									fontSize: 12,
								},
							},
							color: function(params) {
								var colorList = ['#c23531','#2f4554', '#61a0a8', '#d48265', '#91c7ae','#749f83', '#ca8622'];
								return colorList[params.dataIndex % colorList.length];
							}
						},
					},
				}]
			}],
			i = e("#LAY-index-dataview").children("div"),
			n = function(e) {
				l[e] = a.init(i[e], layui.echartsTheme);
				l[e].setOption(t[e]);
				window.onresize = l[e].resize;
			};

		// 获取数据并渲染图表
		$.ajax({
			type: 'GET',
			url: '/bar/',
			success: function(res) {
				if (res.Code === 0) {
					if (res.bar_x.length === 0) {
						layer.msg('暂无数据');
						return;
					}
					t[0].xAxis[0].data = res.bar_x;
					t[0].series[0].data = res.bar_y;
					i[0] && n(0);
				} else {
					layer.msg(res.msg || '获取数据失败');
				}
			},
			error: function(response) {
				layer.msg('服务器错误，请稍后重试');
			}
		});
	}), e("console", {})
});