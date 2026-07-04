"""
Flask 主应用
提供 Ubuntu 端所有 REST API 接口
"""
import os
import uuid
from datetime import datetime
from pathlib import Path

# 自动加载 .env 文件到环境变量
_ENV_PATH = Path(__file__).resolve().parent / ".env"
if _ENV_PATH.exists():
    with open(_ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key and not os.environ.get(key):
                    os.environ[key] = value

from flask import Flask, request, jsonify, send_from_directory, render_template

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
    return jsonify({"code": code, "data": data or {}, "msg": msg}), 200


# ==================== 前端页面 ====================
@app.route("/")
def index():
    """首页看板"""
    return render_template("index.html")


# ==================== 拍题识别 ====================
@app.route("/api/photo/recognize", methods=["POST"])
def recognize_photo():
    """高拍仪照片上传 → Claude Vision 识别（支持多题 + 批改痕迹）"""
    if "image" not in request.files:
        return error_response(1, "缺少图片文件")

    image_file = request.files["image"]
    if image_file.filename == "":
        return error_response(1, "图片文件名为空")

    subject = request.form.get("subject", "math")
    description = request.form.get("description", "")

    logger.info(f"收到照片识别请求: subject={subject}, file={image_file.filename}")

    # 读取图片数据
    image_data = image_file.read()

    # 导入 OCR 引擎（延迟导入避免启动慢）
    from modules.ocr_recognition import PhotoRecognitionEngine
    engine = PhotoRecognitionEngine()

    result = engine.recognize_photo(image_data, subject, description)

    if "error" in result:
        return error_response(2, f"识别失败: {result['error']}")

    # 自动入库错题（如果用户选择了添加）
    add_to_error_book = request.form.get("add_to_error_book", "false") == "true"
    if add_to_error_book and result.get("batch"):
        from modules.error_book import add_error_record
        wrong_count = 0
        for q in result.get("wrong_questions", []):
            record_id = add_error_record(
                question_id=f"{subject}_q{q.get('question_num', 0)}",
                subject=subject,
                problem_text=q.get("recognized_text", ""),
                latex=q.get("latex", ""),
                knowledge_points=q.get("knowledge_points", []),
                correct_answer=q.get("standard_answer", ""),
                difficulty=q.get("difficulty", "medium"),
                wrong_answer=q.get("student_answer", ""),
                comment=q.get("comment", ""),
            )
            q["error_record_id"] = record_id
            wrong_count += 1
        result["wrong_records_added"] = wrong_count
        logger.info(f"自动入库错题: {wrong_count} 道")

    return success_response(data=result)


# ==================== 错题本 ====================
@app.route("/api/error_book", methods=["GET", "POST"])
@app.route("/api/error_book/<record_id>", methods=["DELETE", "GET"])
def error_book(record_id=None):
    from modules.error_book import get_error_list, add_error_record, delete_error_record, get_error_detail

    if record_id:
        if request.method == "DELETE":
            delete_error_record(record_id)
            return success_response(msg="错题已删除")
        if request.method == "GET":
            detail = get_error_detail(record_id)
            if not detail:
                return error_response(1, "错题不存在")
            return success_response(data=detail)

    if request.method == "POST":
        data = request.get_json()
        if not data or "question_id" not in data:
            return error_response(1, "缺少必要参数: question_id")

        record_id = add_error_record(
            question_id=data["question_id"],
            subject=data.get("subject", "math"),
            problem_text=data.get("problem_text", ""),
            latex=data.get("latex", ""),
            knowledge_points=data.get("knowledge_points", []),
            wrong_answer=data.get("wrong_answer", ""),
            correct_answer=data.get("correct_answer", ""),
            difficulty=data.get("difficulty", "medium"),
        )
        return success_response(data={"record_id": record_id}, msg="错题已添加")

    # GET: 查询错题列表
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    subject = request.args.get("subject")

    result = get_error_list(page, page_size, subject)
    return success_response(data=result)


# ==================== 出卷 ====================
@app.route("/api/exam/generate", methods=["POST"])
def generate_exam():
    from modules.exam_module import ExamGenerator

    data = request.get_json()
    if not data or "subject" not in data or "grade" not in data:
        return error_response(1, "缺少必要参数: subject, grade")

    generator = ExamGenerator()
    result = generator.generate_exam(
        subject=data["subject"],
        grade=data["grade"],
        chapter=data.get("chapter", ""),
        question_count=data.get("question_count", 20),
        include_answer=data.get("include_answer", True),
    )

    if "error" in result:
        return error_response(2, f"生成失败: {result['error']}")

    return success_response(data=result)


@app.route("/api/exam/grade", methods=["POST"])
def grade_exam():
    from modules.exam_module import ExamGrader

    if "images" not in request.files:
        return error_response(1, "缺少答卷图片")

    exam_id = request.form.get("exam_id", "")
    questions_json = request.form.get("questions", "[]")

    grader = ExamGrader()
    result = grader.grade_exam(exam_id, request.files["images"].read(), [])

    return success_response(data=result)


# ==================== 语音识别 ====================
@app.route("/api/speech/transcribe", methods=["POST"])
def speech_transcribe():
    """通用语音转文字接口"""
    if "audio" not in request.files:
        return error_response(1, "缺少音频文件")

    audio_file = request.files["audio"]
    language = request.form.get("language", "zh")

    audio_data = audio_file.read()
    from modules.speech_to_text import get_speech_engine
    engine = get_speech_engine()
    text = engine.transcribe(audio_data=audio_data, language=language)

    if not text:
        return error_response(2, "语音识别失败，请检查音频质量或 Whisper 模型")

    return success_response(data={"text": text, "language": language})


# ==================== 英语口语 ====================
@app.route("/api/english/dialogue", methods=["POST"])
def english_dialogue():
    from modules.english_module import EnglishDialogueEngine

    if "audio" not in request.files:
        return error_response(1, "缺少音频文件")

    audio_file = request.files["audio"]
    mode = request.form.get("mode", "free_talk")
    topic = request.form.get("topic", "")

    engine = EnglishDialogueEngine()
    result = engine.process_dialogue(audio_file.read(), mode, topic)

    if "error" in result:
        return error_response(2, f"处理失败: {result['error']}")

    return success_response(data=result)


# ==================== 目标奖励 ====================
@app.route("/api/goal", methods=["GET", "POST"])
def goals():
    from modules.goal_system import create_goal, get_goals, get_points_balance

    if request.method == "POST":
        data = request.get_json()
        if not data or "title" not in data or "target_points" not in data:
            return error_response(1, "缺少必要参数: title, target_points")

        goal_id = create_goal(
            title=data["title"],
            target_points=data["target_points"],
            description=data.get("description", ""),
            deadline=data.get("deadline"),
        )
        return success_response(data={"goal_id": goal_id}, msg="目标已创建")

    status = request.args.get("status")
    goals_list = get_goals(status)
    points = get_points_balance()

    return success_response(data={"goals": goals_list, "points": points})


@app.route("/api/goal/<goal_id>/redeem", methods=["POST"])
def redeem_goal(goal_id):
    from modules.goal_system import redeem_goal

    data = request.get_json()
    if not data or "reward_type" not in data:
        return error_response(1, "缺少必要参数: reward_type")

    result = redeem_goal(goal_id, data["reward_type"], data.get("reward_description", ""))

    if "error" in result:
        return error_response(1, result["error"])

    return success_response(data=result, msg="兑换申请已提交")


# ==================== 学习摘要 ====================
@app.route("/api/summary/daily", methods=["GET"])
def daily_summary():
    from modules.error_book import get_today_stats
    from modules.goal_system import get_points_balance

    stats = get_today_stats()
    points = get_points_balance()

    return success_response(data={
        "date": stats.get("date", ""),
        "completed_tasks": stats.get("completed_tasks", 0),
        "total_tasks": stats.get("total_tasks", 0),
        "new_errors": stats.get("new_errors", 0),
        "pending_reviews": stats.get("pending_reviews", 0),
        "weak_points": [],  # TODO: 从知识图谱获取
        "tomorrow_suggestions": "",  # TODO: 从诊断引擎生成
        "earned_points": points.get("total_points", 0),
    })


# ==================== 知识图谱 ====================
@app.route("/api/knowledge/graph", methods=["GET"])
def knowledge_graph():
    from modules.knowledge_graph import get_knowledge_graph

    subject = request.args.get("subject")
    result = get_knowledge_graph(subject)

    return success_response(data=result)


# ==================== 家长消息 ====================
# （新版实现见下方）


# ==================== 看板数据 ====================
@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    from modules.error_book import get_today_stats
    from modules.goal_system import get_goals, get_points_balance

    stats = get_today_stats()
    goals_list = get_goals("active")
    points = get_points_balance()

    return success_response(data={
        "today_stats": stats,
        "active_goals": goals_list,
        "points": points,
        "pending_reviews": [],  # TODO: 从错题本获取待复习
    })


# ==================== 积分查询 ====================
@app.route("/api/points", methods=["GET"])
def points():
    from modules.goal_system import get_points_balance

    result = get_points_balance()
    return success_response(data=result)


# ==================== 健康检查 ====================
@app.route("/api/health", methods=["GET"])
def health():
    return success_response(data={"status": "ok"})


# ==================== 学生档案 ====================
@app.route("/api/student/profile", methods=["GET", "POST"])
def student_profile():
    if request.method == "GET":
        rows = execute_query("SELECT * FROM users WHERE user_id = 1")
        if rows:
            return success_response(data=rows[0])
        return error_response(1, "未找到学生档案")

    # POST: 更新档案
    data = request.get_json()
    if not data:
        return error_response(1, "缺少请求数据")

    name = data.get("name")
    grade = data.get("grade")
    avatar_url = data.get("avatar_url")

    if not name and not grade and not avatar_url:
        return error_response(1, "至少提供一个要更新的字段")

    sets = []
    params = []
    for field in ("name", "grade", "avatar_url"):
        val = data.get(field)
        if val is not None:
            sets.append(f"{field} = ?")
            params.append(val)

    params.append(1)  # user_id
    sql = f"UPDATE users SET {', '.join(sets)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?"
    execute_write(sql, tuple(params))

    logger.info(f"学生档案已更新: {data}")
    return success_response(msg="档案已更新")


# ==================== 诊断引擎 ====================
@app.route("/api/diagnose/generate", methods=["POST"])
def diagnose_generate():
    from modules.diagnosis_engine import DiagnosisEngine

    data = request.get_json()
    if not data or "subject" not in data or "grade" not in data:
        return error_response(1, "缺少必要参数: subject, grade")

    engine = DiagnosisEngine()
    result = engine.generate_diagnosis(
        subject=data["subject"],
        grade=data["grade"],
        chapter=data.get("chapter", ""),
        question_count=data.get("question_count", 20),
    )

    if "error" in result:
        return error_response(2, f"诊断出题失败: {result['error']}")

    return success_response(data=result)


@app.route("/api/diagnose/answer", methods=["POST"])
def diagnose_answer():
    """提交答题结果"""
    data = request.get_json()
    if not data or "answers" not in data:
        return error_response(1, "缺少必要参数: answers")

    from modules.diagnosis_engine import DiagnosisEngine
    engine = DiagnosisEngine()

    answers = data["answers"]
    result = engine.analyze_behavior_metrics(answers)

    if "error" in result:
        return error_response(2, f"分析失败: {result['error']}")

    return success_response(data=result)


@app.route("/api/diagnose/report", methods=["GET"])
def diagnose_report():
    """获取诊断报告"""
    question_id = request.args.get("question_id")
    if not question_id:
        return error_response(1, "缺少参数: question_id")

    # 从错题本获取题目详情
    from modules.error_book import get_error_detail
    detail = get_error_detail(question_id)
    if not detail:
        return error_response(1, "未找到该题目")

    return success_response(data={
        "question": detail,
        "knowledge_points": detail.get("knowledge_details", []),
        "reviews": detail.get("reviews", []),
    })


# ==================== 语音提醒 ====================
@app.route("/api/voice/reminders", methods=["GET"])
def get_reminders():
    """获取所有定时提醒"""
    from modules.reminder import _reminders
    return success_response(data={"reminders": _reminders})


@app.route("/api/voice/reminders", methods=["POST"])
def add_reminder_api():
    """添加定时提醒"""
    data = request.get_json()
    if not data or "time" not in data or "message" not in data:
        return error_response(1, "缺少必要参数: time, message")

    from modules.reminder import add_reminder
    reminder_id = add_reminder(data["time"], data["message"])
    return success_response(data={"reminder_id": reminder_id}, msg="提醒已添加")


@app.route("/api/voice/reminders/<rid>", methods=["DELETE"])
def delete_reminder_api(rid):
    """删除定时提醒"""
    # 简化实现：从 _reminders 列表中移除
    from modules.reminder import _reminders
    original_len = len(_reminders)
    for i, r in enumerate(_reminders):
        if r["id"] == rid:
            _reminders.pop(i)
            break
    if len(_reminders) == original_len:
        return error_response(1, "提醒不存在")
    return success_response(msg="提醒已删除")


# ==================== 文件上传 ====================
UPLOAD_DIR = BASE_DIR / "data" / "uploads"


@app.route("/api/upload/file", methods=["POST"])
def upload_file():
    """上传文件（图片、音频等）"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    if "file" not in request.files:
        return error_response(1, "缺少文件")

    file = request.files["file"]
    if file.filename == "":
        return error_response(1, "文件名为空")

    # 生成安全文件名
    import uuid
    ext = Path(file.filename).suffix or ".bin"
    safe_name = f"{uuid.uuid4().hex[:12]}{ext}"
    dest = UPLOAD_DIR / safe_name
    file.save(str(dest))

    logger.info(f"文件已上传: {safe_name} ({dest.stat().st_size} bytes)")
    return success_response(data={
        "filename": safe_name,
        "original_name": file.filename,
        "size": dest.stat().st_size,
        "url": f"/api/upload/files/{safe_name}",
    })


@app.route("/api/upload/files/<filename>", methods=["GET"])
def serve_uploaded_file(filename):
    """提供已上传文件的访问"""
    return send_from_directory(str(UPLOAD_DIR), filename)


# ==================== 家长消息（完善版）====================
@app.route("/api/parent/message", methods=["POST"])
def parent_message():
    from modules.parent_notify import send_serverchan, send_parent_message

    data = request.get_json()
    if not data or "message" not in data:
        return error_response(1, "缺少必要参数: message")

    sender = data.get("sender", "家长")
    message = data["message"]
    notify = data.get("notify", False)  # 是否同时推送 ServerChan

    logger.info(f"收到家长消息: sender={sender}")

    # 存入数据库
    import uuid
    msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    execute_write(
        """INSERT INTO parent_messages
           (message_id, sender, content, display_status, created_at)
           VALUES (?, ?, ?, 'pending', ?)""",
        (msg_id, sender, message, datetime.now().isoformat()),
    )

    # 可选推送
    pushed = False
    if notify:
        pushed = send_parent_message(sender, message)

    return success_response(data={"message_id": msg_id, "pushed": pushed}, msg="消息已接收")


# ==================== 家长消息查询 ====================
@app.route("/api/parent/messages", methods=["GET"])
def get_parent_messages():
    """获取家长消息列表"""
    rows = execute_query(
        "SELECT * FROM parent_messages ORDER BY created_at DESC LIMIT 50"
    )
    return success_response(data={"messages": rows})


# ==================== 课本同步 ====================
@app.route("/api/textbook/sync", methods=["POST"])
def textbook_sync():
    """课本目录识别 + 进度匹配"""
    if "image" not in request.files:
        return error_response(1, "缺少课本图片")

    image_file = request.files["image"]
    if image_file.filename == "":
        return error_response(1, "图片文件名为空")

    grade = request.form.get("grade", "")
    subject = request.form.get("subject", "math")

    from modules.textbook_sync import TextbookSyncEngine
    engine = TextbookSyncEngine()

    image_data = image_file.read()
    result = engine.identify_chapters(image_data, grade, subject)

    if "error" in result:
        return error_response(2, f"目录识别失败: {result['error']}")

    return success_response(data=result)


@app.route("/api/textbook/progress", methods=["POST"])
def textbook_progress():
    """匹配学习进度"""
    data = request.get_json()
    if not data or "completed_chapters" not in data:
        return error_response(1, "缺少参数: completed_chapters")

    from modules.textbook_sync import TextbookSyncEngine
    engine = TextbookSyncEngine()

    result = engine.match_progress(
        data["completed_chapters"],
        data.get("textbook_chapters", []),
    )

    if "error" in result:
        return error_response(2, result["error"])

    return success_response(data=result)


@app.route("/api/textbook/questions", methods=["POST"])
def textbook_questions():
    """根据进度生成拓展题"""
    data = request.get_json()
    if not data or "chapters" not in data:
        return error_response(1, "缺少参数: chapters")

    from modules.textbook_sync import TextbookSyncEngine
    engine = TextbookSyncEngine()

    result = engine.generate_extension_questions(
        subject=data.get("subject", "math"),
        grade=data.get("grade", ""),
        chapters=data["chapters"],
        count=data.get("count", 10),
    )

    if "error" in result:
        return error_response(2, f"拓展题生成失败: {result['error']}")

    return success_response(data=result)


# ==================== 每日推送 ====================
@app.route("/api/push/daily", methods=["POST"])
def push_daily():
    """触发每日学习摘要推送"""
    from modules.error_book import get_today_stats
    from modules.goal_system import get_points_balance
    from modules.parent_notify import send_daily_summary

    stats = get_today_stats()
    points = get_points_balance()

    stats["date"] = stats.get("date", datetime.now().strftime("%Y-%m-%d"))
    stats["completed_tasks"] = stats.get("pending_reviews", 0)  # 简化
    stats["total_tasks"] = stats.get("pending_reviews", 0) + stats.get("new_errors", 0)
    stats["earned_points"] = points.get("total_points", 0)

    success = send_daily_summary(stats)
    return success_response(data={"sent": success}, msg="推送完成" if success else "Token 未配置，已记录日志")


# ==================== 错题复习 ====================
@app.route("/api/error_book/review", methods=["POST"])
def review_error():
    """记录错题复习结果"""
    data = request.get_json()
    if not data or "record_id" not in data:
        return error_response(1, "缺少参数: record_id")

    from modules.error_book import record_review
    result = record_review(data["record_id"], data.get("is_correct", False))

    if "error" in result:
        return error_response(1, result["error"])

    # 复习正确奖励积分
    if result.get("is_mastered", False):
        from modules.goal_system import earn_points
        earn_points("error_review", data["record_id"], 10, f"掌握错题: {data['record_id']}")

    return success_response(data=result, msg="复习记录已保存")


@app.route("/api/error_book/pending", methods=["GET"])
def get_pending_reviews():
    """获取待复习错题"""
    from modules.error_book import get_pending_reviews
    items = get_pending_reviews()
    return success_response(data={"items": items, "total": len(items)})


# ==================== 知识点管理 ====================
@app.route("/api/knowledge/weak-points", methods=["GET"])
def weak_points():
    """获取薄弱知识点"""
    from modules.knowledge_graph import get_weak_points
    subject = request.args.get("subject")
    threshold = request.args.get("threshold", 0.6, type=float)
    points = get_weak_points(subject=subject, threshold=threshold)
    return success_response(data={"weak_points": points})


# ==================== 分数趋势 ====================
@app.route("/api/dashboard/stats/trend", methods=["GET"])
def score_trend():
    """获取最近7天的分数趋势"""
    from datetime import timedelta
    trend = []
    for i in range(7, 0, -1):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        # 查询当天的考试记录
        rows = execute_query(
            """SELECT ea.total_score, e.subject
               FROM exam_attempts ea
               JOIN exams e ON ea.exam_id = e.exam_id
               WHERE date(ea.started_at) = ?""",
            (day,),
        )
        if rows:
            trend.append({
                "date": day,
                "scores": [r["total_score"] for r in rows],
            })
        else:
            trend.append({"date": day, "scores": []})

    return success_response(data={"trend": trend})


# ==================== 错题分布 ====================
@app.route("/api/dashboard/stats/errors", methods=["GET"])
def error_distribution():
    """获取错题学科分布"""
    rows = execute_query(
        """SELECT subject, COUNT(*) as cnt
           FROM error_records
           GROUP BY subject
           ORDER BY cnt DESC"""
    )
    subjects = {"math": "数学", "chinese": "语文", "english": "英语", "physics": "物理", "chemistry": "化学"}
    result = [{"name": subjects.get(r["subject"], r["subject"]), "value": r["cnt"]} for r in rows]
    return success_response(data={"distribution": result})


# ==================== 知识点掌握度 ====================
@app.route("/api/dashboard/stats/mastery", methods=["GET"])
def mastery_stats():
    """获取知识点掌握度统计"""
    rows = execute_query(
        """SELECT subject, name, mastery_level
           FROM knowledge_points
           ORDER BY mastery_level ASC"""
    )
    return success_response(data={"points": rows})


# ==================== 启动 ====================
def create_tables():
    """初始化数据库表"""
    schema_path = BASE_DIR / "db_schema.sql"
    init_db(str(schema_path))


if __name__ == "__main__":
    # 初始化数据库
    create_tables()

    # 启动定时提醒调度器（后台线程）
    import threading
    from modules.reminder import start_scheduler, add_reminder

    # 从配置加载提醒计划
    from common.config import get_all
    config = get_all()
    reminder_schedule = config.get("reminder", {}).get("schedule", [])
    boot_message = config.get("reminder", {}).get("boot_message", "早安！今天也要加油学习哦~")

    # 注册提醒
    if boot_message:
        add_reminder("07:00", boot_message)
    for item in reminder_schedule:
        add_reminder(item["time"], item["message"])

    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("🔄 定时提醒调度器已启动")

    # 启动服务
    host = get_config("app", "host", "0.0.0.0")
    port = get_config("app", "port", 5000)
    debug = get_config("app", "debug", False)

    logger.info(f"🚀 AI学习教练系统启动: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
