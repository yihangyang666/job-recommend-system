/** layuiAdmin.std-v1.0.0 LPPL License By http://www.layui.com/admin/ */ ;
layui.define(["table", "form"], function(exports) {
	var $ = layui.$,
		table = layui.table,
		form = layui.form;

	//职位列表管理
	table.render({
		elem: "#LAY-app-forum-list",
		url: "/get_job_list/",
		cols: [
			[{
				field: "_id",
				title: "职位编号",
				width: 180
			}, {
				field: "name",
				title: "职位名称",
				width: 200
			}, {
				field: "salary",
				title: "薪资待遇",
				width: 100
			}, {
				field: "education",
				title: "学历要求",
				width: 100
			}, {
				field: "experience",
				title: "经验要求",
				width: 100
			}, {
				field: "place",
				title: "工作地点",
				width: 100
			}, {
				field: "company",
				title: "公司名称",
				width: 200
			}, {
				field: "company_type",
				title: "所属行业",
				width: 120
			}, {
				field: "company_size",
				title: "公司规模",
				width: 120
			}, {
				field: "status",
				title: "状态",
				width: 100,
				templet: function(d) {
					if (d.status === '已投递') {
						return '<span class="layui-badge layui-bg-green">已投递</span>';
					}
					return '';
				}
			}, {
				title: "操作",
				width: 150,
				align: "center",
				fixed: "right",
				toolbar: "#table-forum-list"
			}]
		],
		page: true,
		limit: 15,
		text: {
			none: "暂无数据"
		}
	});

	//监听工具条
	table.on("tool(LAY-app-forum-list)", function(obj) {
		var data = obj.data;
		if (obj.event === "send") {
			layer.confirm("确定投递职位 " + data.name + " 吗？", function(index) {
				$.ajax({
						type: 'POST',
						data: {
							"job_id": data._id,
							"send_key": data.send_key || 0
						},
						url: '/send_job/',
						success: function(res) {
							layer.msg(res.msg);
							if (res.Code === 0) {
								table.reload('LAY-app-forum-list');
							}
						},
						error: function(xhr) {
							layer.msg('操作失败，请稍后重试');
						}
					});
				layer.close(index);
			});
		} else if (obj.event === "send_1") {
			layer.confirm("确定取消投递 " + data.name + " 吗？", function(index) {
				$.ajax({
						type: 'POST',
						data: {
							"job_id": data._id,
							"send_key": 1
						},
						url: '/send_job/',
						success: function(res) {
							layer.msg(res.msg);
							if (res.Code === 0) {
								table.reload('LAY-app-forum-list');
							}
						},
						error: function(xhr) {
							layer.msg('操作失败，请稍后重试');
						}
					});
				layer.close(index);
			});
		}
	});

	exports('forum', {})
});
