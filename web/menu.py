# 菜单对应关系，配置WeChat应用中配置的菜单ID与执行命令的对应关系，需要手工修改
# 菜单序号在https://work.weixin.qq.com/wework_admin/frame#apps 应用自定义菜单中维护，然后看日志输出的菜单序号是啥（按顺利能猜到的）....
# 命令对应关系：/qbt qBittorrent转移；/qbr qBittorrent删种；/hotm 热门预告；/pts PT签到；/mrt 预告片下载；/rst ResilioSync同步；/rss RSS下载
WECHAT_MENU = {"_0_0": "/qbt", "_0_1": "/qbr", "_0_2": "/rss", "_0_3": "/hotm", "_0_4": "/mrt", "_1_0": "/rst",
               "_2_0": "/pts"}
