# 个人AI学习教练系统 V1.0
> Ubuntu端开发环境

## 项目简介
打造一个"会自己备课、会自己充电、会越教越好"的AI家庭教师系统。
为自家孩子提供完整的学习教练闭环（诊断、错题、出卷阅卷、英语、看板、语音提醒、目标奖励）。

## 双端架构
- **Ubuntu端**：核心AI逻辑、后端API、数据库、前端页面、Whisper部署
- **Windows端**：高拍仪、录音、打印、TTS语音、开机启动、目标奖励系统前端

## Git协同
- Ubuntu端代码提交到 `auto-ubuntu` 分支
- Windows端代码提交到 `auto-win` 分支
- 每天 22:30 合并到 `main`
- `common/` 目录唯一修改权在Ubuntu端

## 目录结构
```
ai-study-coach/
├── common/              # 公共模块（Ubuntu独有修改权）
├── contracts/           # API接口契约
├── modules/             # 业务模块
├── static/              # 前端静态资源
├── templates/           # HTML模板
├── verify/              # 验证脚本
├── tools/               # 外部工具（SumatraPDF等）
├── tests/               # 测试
├── app.py               # Flask主应用
├── main.py              # 主程序入口
├── db_schema.sql        # 数据库schema
├── config.yaml          # 配置文件
└── requirements.txt     # Python依赖
```
