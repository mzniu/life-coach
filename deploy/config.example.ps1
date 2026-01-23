# Life Coach 部署配置文件（示例）
# 复制此文件为 config.ps1 并修改为你的实际配置
# 重要：config.ps1 已被 .gitignore 排除，不会被提交到 Git

# 树莓派配置
$PI_HOST = "192.168.1.100"      # 树莓派 IP 地址
$PI_USER = "pi"                  # SSH 用户名
$PI_PATH = "/home/pi/LifeCoach" # 远程安装路径

# Resilio Sync 配置
$RESILIO_USERNAME = "admin"          # Web 界面用户名
$RESILIO_PASSWORD = "your-password"  # Web 界面密码（建议修改）

# 导出变量供脚本使用
Export-ModuleMember -Variable PI_HOST, PI_USER, PI_PATH, RESILIO_USERNAME, RESILIO_PASSWORD
