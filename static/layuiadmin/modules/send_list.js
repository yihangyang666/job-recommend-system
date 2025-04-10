/** layuiAdmin.std-v1.0.0 LPPL License By http://www.layui.com/admin/ */ ;
layui.define(["table", "form"], function(e) {
	var t = layui.$,
		i = layui.table,
		$=layui.jquery;
	layui.form;

	// 获取CSRF Token
	function getCsrfToken() {
		return document.querySelector('[name=csrfmiddlewaretoken]').value;
	}

	i.render({
		elem: "#LAY-app-forum-list",
		url: "/send_list/",  // 使用相对路径
		cols: [
			[{
				field: "job_id",
				title: "职位编号",
				width: 100
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
				field: "created_at",
				title: "投递时间",
				width: 160
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
	}),
		i.on('tool(LAY-app-forum-list)', function(obj) {
			var data = obj.data;
			console.log('当前行数据:', data);  // 调试用
			if(obj.event === 'send') {
				layer.confirm('确定投递职位 "' + data.name + '" 吗？', function(index) {
					$.ajax({
						type: 'POST',
						data: {
							"job_id": data.job_id || data._id,
							"send_key": 0
						},
						url: '/send_job/',
						success: function(res) {
							layer.msg(res.msg);
							if(res.Code === 0) {
								i.reload('LAY-app-forum-list');
							}
						},
						error: function(xhr) {
							layer.msg('操作失败，请稍后重试');
						}
					});
					layer.close(index);
				});
			} else if(obj.event === 'send_1') {
				layer.confirm('确定取消投递 "' + data.name + '" 吗？', {
					title: '确认',
					btn: ['确定', '取消']
				}, function(index) {
					// 获取CSRF token
					var csrftoken = t('input[name="csrfmiddlewaretoken"]').val();
					
					t.ajax({
						type: 'POST',
						url: '/send_job/',
						data: {
							"job_id": data.job_id || data._id,  // 尝试两个可能的字段
							"send_key": 1
						},
						headers: {
							"X-CSRFToken": csrftoken
						},
						success: function(res) {
							console.log('服务器响应:', res);  // 调试用
							if(res.Code === 0) {
								layer.msg('取消投递成功');
								// 重新加载表格数据
								i.reload('LAY-app-forum-list', {
									page: {
										curr: 1
									}
								});
							} else {
								layer.msg(res.msg || '操作失败');
							}
						},
						error: function(xhr, status, error) {
							console.log('错误信息:', error);  // 调试用
							layer.msg('网络错误，请稍后重试');
						}
					});
					layer.close(index);
				});
			}
		});
	e("send_list", {});
});
