from flask import Flask, jsonify, request, make_response, g
from flask_cors import CORS
from forms import *
from schemas import *
import os
import json
import logging
import asyncio
from aiogram.types import FSInputFile
import csv
from uuid import uuid4
from methodics_analyzer import MethodicsAnalyzer
from report_processor import initialize_evaluator
import threading
from bot import bot
import urllib.parse

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['UPLOAD_FOLDER_1'] = 'static/method'
app.config['UPLOAD_FOLDER_2'] = 'static/labs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

evaluator = initialize_evaluator()

if not os.path.exists(app.config['UPLOAD_FOLDER_1']):
    os.makedirs(app.config['UPLOAD_FOLDER_1'])
if not os.path.exists(app.config['UPLOAD_FOLDER_2']):
    os.makedirs(app.config['UPLOAD_FOLDER_2'])

TASKS = {}

LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(LOOP)

@app.route("/manual", methods=["POST"])
def manual():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({"status": "Error", "reason": "Файл не передан"}), 400
            
        task_id = str(uuid4())
        filename = f"{task_id}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER_1'], filename)
        
        file.save(filepath)
        
        TASKS[task_id] = {
            "status": "processing",
            "summary": None,
            "error": None
        }
        
        threading.Thread(target=analyze_methodics, args=(task_id, filepath)).start()
        
        return jsonify({"taskId": task_id}), 200
    except Exception as e:
        return jsonify({"status": "Error", "reason": str(e)}), 500

def analyze_methodics(task_id, filepath):
    try:
        analyzer = MethodicsAnalyzer()
        result = analyzer.analyze(filepath)
        
        if "error" in result:
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["error"] = result["error"]
        else:
            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["summary"] = {
                "requirements": result.get("requirements", []),
                "summary": result.get("summary", [])
            }
    except Exception as e:
        TASKS[task_id]["status"] = "failed"
        TASKS[task_id]["error"] = str(e)

@app.route("/status/<task_id>", methods=["GET"])
def status(task_id):
    try:
        task = TASKS.get(task_id)
        if not task:
            return jsonify({"status": "failed", "error": "Задача не найдена"}), 404
        
        return jsonify(task), 200
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500
    
@app.route("/loading-report", methods=["POST"])
def report():
    form = ReportForm()
    if form.validate_on_submit():
        try:
            filename = form.file.data.filename
            filepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER_2'], filename))
            form.file.data.save(filepath)
            
            summary = json.loads(request.form.get('summary', '{}'))
            criteria = json.loads(request.form.get('criteria', '[]'))
            
            results = evaluator.evaluate(
                filepath,
                criteria,
                summary.get('requirements', []),
                summary.get('summary', [])
            )
            formatted_results = [
                {
                    "criteria": item["criteria"],
                    "score": item["score"],
                    "comment": item["comment"]
                } for item in results.get("results", [])
            ]
            
            return jsonify({
                "status": "success",
                "results": formatted_results,
                "author": results.get("author", "Неизвестный автор")
            }), 200
        except Exception as e:
            return jsonify({"status": "Error", "reason": str(e)}), 500
    return jsonify({"status": "Error", "reason": "Форма не валидна"}), 400

@app.route("/criteria", methods=["POST"])
def criteria():
    try:
        req = request.json
        criteria = Criteria(criteria=req["criteria"], score=req["score"])
        return jsonify({"status": "OK"}), 200
    except Exception as e:
        return jsonify({"status": "Error", "reason": str(e)}), 500
    
@app.route("/send-report", methods=["POST"])
def send_report():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({"status": "Error", "reason": "Файл не передан"}), 400
            
        allowed_formats = ('docx', 'pdf', 'xlsx', 'pptx')
        if not file.filename.lower().endswith(allowed_formats):
            return jsonify({"status": "Error", "reason": f"Поддерживаются только {', '.join(allowed_formats)}"}), 400
            
        filename = file.filename
        filename = urllib.parse.unquote(filename) 
        parts = filename.rsplit('_report', 1) 
        
        if len(parts) != 2 or not parts[0]:
            return jsonify({"status": "Error", "reason": "Некорректное имя файла"}), 400
            
        full_name = parts[0].replace('_', ' ')
        name = full_name.split()[0]
        user_id = None
        with open("users.csv", mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if name.lower() in row[1].strip().lower():
                    user_id = int(row[0])
                    break
        print(user_id)            
        if not user_id:
            return jsonify({"status": "Error", "reason": "Пользователь не найден"}), 404
            
        filepath = os.path.join(app.config['UPLOAD_FOLDER_2'], filename)
        file.save(filepath)
        
        threading.Thread(target=send_document, args=(user_id, filepath, filename)).start()
        
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.error(f"Критическая ошибка: {str(e)}")
        return jsonify({"status": "Error", "reason": "Внутренняя ошибка сервера"}), 500

def send_document(user_id, filepath, filename):
    try:
        LOOP.run_until_complete(
            bot.send_document(
                chat_id=user_id,
                document=FSInputFile(filepath),
                caption=f"Ваш отчет: {filename}"
            )
        )
    except Exception as e:
        logging.error(f"Ошибка отправки файла: {str(e)}")

    
if __name__ == "__main__":
    app.run(debug=True)
