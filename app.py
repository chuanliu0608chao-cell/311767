"""
Flask 主应用
提供 Ubuntu 端所有 REST API 接口
"""
import os
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

from common.config import get_config
from common.logger import logger
from common.database import init_db, execute_query, execute_write

# 创建 Flask 应用
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "study-coach-dev-key")

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent


@app.before_request
def log_request():
    """记录每个请求"""
    logger.debug(f"{request.method} {request.path} from {request.remote_addr}")


@app.after_request
def log_response(response):
    """记录响应状态"""
    logger.debug(f"Response {response.status_code} for {request.path}")
    return response


# ==================== 统一响应格式 ====================
def success_response(data=None, msg=""):
    """成功响应"""
    return jsonify({"code": 0, "data": data or {}, "msg": msg}), 200


def error_response(code, msg, data=None):
    """错误响应"""
    return jsonify({"code": code, "data": data or {}, "msg": msg}), 200  # 业务错误仍返回 200


# ==================== 拍题识别 ====================
@app.route("/api/photo/recognize", methods=["POST"])
def recognize_photo():
    """高拍仪照片上传 → GLM-4V识别"""
    if "image" not in request.files:
        return error_response(1, "缺少图片文件")

    image_file = request.files["image"]
    if image_file.filename == "":
        return error_response(1, "图片文件名为空")

    subject = request.form.get("subject", "math")
    description = request.form.get("description", "")

    logger.info(f"收到照片识别请求: subject={subject}, file={image_file.filename}")

    # TODO: 保存图片 → 调用 GLM-4V API → 返回识别结果
    # 这里先返回占位数据
    return success_response(
        data={
            "question_id": f"q_{os.urandom(4).hex()}",
            "recognized_text": "[待识别]",
            "latex": "",
            "knowledge_points": [],
            "difficulty": "medium",
        },
        msg="照片已接收，AI识别中..."
    )


# ==================== 错题本 ====================
@app.route("/api/error_book", methods=["GET", "POST"])
def error_book():
    if request.method == "POST":
        # 添加错题
        data = request.get_json()
        if not data or "question_id" not in data:
            return error_response(1, "缺少必要参数: question_id")

        logger.info(f"添加错题: {data.get('question_id')}")
        # TODO: 写入数据库
        return success_response(msg="错题已添加")

    # GET: 查询错题列表
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    subject = request.args.get("subject")

    logger.info(f"查询错题列表: page={page}, subject={subject}")
    # TODO: 从数据库查询
    return success_response(data={"items": [], "total": 0, "page": page, "page_size": page_size})


# ==================== 出卷 ====================
@app.route("/api/exam/generate", methods=["POST"])
def generate_exam():
    """使用 DeepSeek 生成试卷"""
    data = request.get_json()
    if not data or "subject" not in data or "grade" not in data:
        return error_response(1, "缺少必要参数: subject, grade")

    logger.info(f"生成试卷: subject={data['subject']}, grade={data['grade']}")
    # TODO: 调用 DeepSeek API 生成题目
    return success_response(data={
        "exam_id": f"exam_{os.urandom(4).hex()}",
        "questions": [],
        "total_score": 100,
    })


@app.route("/api/exam/grade", methods=["POST"])
def grade_exam():
    """答卷批改"""
    if "images" not in request.files:
        return error_response(1, "缺少答卷图片")

    exam_id = request.form.get("exam_id", "")
    logger.info(f"批改答卷: exam_id={exam_id}")
    # TODO: 上传图片 → GLM-4V 批改
    return success_response(data={
        "exam_id": exam_id,
        "total_score": 0,
        "question_scores": [],
    })


# ==================== 英语口语 ====================
@app.route("/api/english/dialogue", methods=["POST"])
def english_dialogue():
    """英语口语对话: 录音 → Whisper识别 → DeepSeek对话 → TTS"""
    if "audio" not in request.files:
        return error_response(1, "缺少音频文件")

    audio_file = request.files["audio"]
    mode = request.form.get("mode", "free_talk")

    logger.info(f"收到英语口语请求: mode={mode}, file={audio_file.filename}")
    # TODO: 保存音频 → Whisper 识别 → DeepSeek 对话 → TTS 生成音频
    return success_response(data={
        "recognized_text": "[待识别]",
        "ai_response": "Hello! Nice to meet you!",
        "tts_audio_url": "",
        "correction": None,
    })


# ==================== 目标奖励 ====================
@app.route("/api/goal", methods=["GET", "POST"])
def goals():
    if request.method == "POST":
        data = request.get_json()
        if not data or "title" not in data or "target_points" not in data:
            return error_response(1, "缺少必要参数: title, target_points")

        logger.info(f"创建目标: {data['title']}")
        # TODO: 写入数据库
        return success_response(data={
            "goal_id": f"goal_{os.urandom(4).hex()}",
            "title": data["title"],
            "target_points": data["target_points"],
            "current_points": 0,
            "status": "active",
            "progress_percent": 0,
        }, msg="目标已创建")

    # GET: 查询目标列表
    logger.info("查询目标列表")
    # TODO: 从数据库查询
    return success_response(data=[])


@app.route("/api/goal/<goal_id>/redeem", methods=["POST"])
def redeem_goal(goal_id):
    """目标兑换"""
    data = request.get_json()
    if not data or "reward_type" not in data:
        return error_response(1, "缺少必要参数: reward_type")

    logger.info(f"兑换目标: {goal_id}, reward_type={data['reward_type']}")
    # TODO: 检查积分 → 冻结 → 推送家长
    return success_response(msg="兑换申请已提交")


# ==================== 学习摘要 ====================
@app.route("/api/summary/daily", methods=["GET"])
def daily_summary():
    """获取每日学习摘要"""
    date = request.args.get("date")
    logger.info(f"获取学习摘要: date={date}")
    # TODO: 统计今日学习数据
    return success_response(data={
        "date": date or "2026-07-03",
        "completed_tasks": 0,
        "total_tasks": 0,
        "weak_points": [],
        "tomorrow_suggestions": "",
        "earned_points": 0,
    })


# ==================== 知识图谱 ====================
@app.route("/api/knowledge/graph", methods=["GET"])
def knowledge_graph():
    """获取知识图谱"""
    logger.info("查询知识图谱")
    # TODO: 从数据库查询知识点和关系
    return success_response(data={
        "nodes": [],
        "edges": [],
    })


# ==================== 家长消息 ====================
@app.route("/api/parent/message", methods=["POST"])
def parent_message():
    """家长消息下发"""
    data = request.get_json()
    if not data or "message" not in data:
        return error_response(1, "缺少必要参数: message")

    sender = data.get("sender", "家长")
    logger.info(f"收到家长消息: sender={sender}")
    # TODO: 存入 parent_messages 表，Windows 端轮询获取
    # TODO: 可选推送 ServerChan
    return success_response(msg="消息已接收")


# ==================== 看板数据 ====================
@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    """获取看板数据"""
    logger.info("查询看板数据")
    # TODO: 聚合查询今日任务、进度、薄弱点等
    return success_response(data={
        "today_tasks": [],
        "progress": {},
        "weak_points": [],
        "pending_reviews": [],
        "earnings_today": 0,
    })


# ==================== 积分查询 ====================
@app.route("/api/points", methods=["GET"])
def points():
    """查询积分"""
    logger.info("查询积分")
    # TODO: 从 points_ledger 统计
    return success_response(data={
        "total_points": 0,
        "frozen_points": 0,
        "recent_transactions": [],
    })


# ==================== 健康检查 ====================
@app.route("/api/health", methods=["GET"])
def health():
    """健康检查"""
    return success_response(data={"status": "ok"})


# ==================== 启动 ====================
def create_tables():
    """初始化数据库表"""
    schema_path = BASE_DIR / "db_schema.sql"
    init_db(str(schema_path))


if __name__ == "__main__":
    # 初始化数据库
    create_tables()

    # 启动服务
    host = get_config("app", "host", "0.0.0.0")
    port = get_config("app", "port", 5000)
    debug = get_config("app", "debug", False)

    logger.info(f"🚀 AI学习教练系统启动: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
