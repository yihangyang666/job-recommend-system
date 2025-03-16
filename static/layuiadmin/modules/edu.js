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
			a = (layui.carousel, layui.echarts),
			l = [],
			t = [{
				title: {
					text: "学历要求分布",
					x: "left",
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
					radius: "80%",
					center: ["50%", "50%"],
					data: []
				}]
			}],
			i = e("#LAY-index-dataview").children("div"),
			n = function(e) {
				l[e] = a.init(i[e], layui.echartsTheme), l[e].setOption(t[e]), window.onresize = l[e].resize
			};

		// 如果容器存在，显示加载动画
		if (i[0]) {
			n(0);
			l[0].showLoading();

			// 获取实际数据
			$.ajax({
				type: 'GET',
				url: '/get_pie/',
				success: function(res) {
					if (res.msg) {
						layer.msg(res.msg);
						return;
					}

					if (!res.edu_data || res.edu_data.length === 0) {
						layer.msg('暂无学历数据');
						return;
					}

					// 更新图表数据
					t[0].series[0].data = res.edu_data;
					if (l[0]) {
						l[0].hideLoading();
						l[0].setOption(t[0]);
					}
				},
				error: function(xhr, status, error) {
					layer.msg('获取数据失败：' + error);
					if (l[0]) {
						l[0].hideLoading();
					}
				}
			});
		}
	}), e("edu", {})
});