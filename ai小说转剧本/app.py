import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
from flask_cors import CORS
CORS(app)
# ==================== 配置区（占位符，请替换为真实值） ====================
LLM_API_KEY = os.environ.get("LLM_API_KEY", "sk-98de18cd0b5243a1ae9227154c9b4096")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "qwen-turbo")
# ======================================================================

SYSTEM_PROMPT = (
    "你是一个专业编剧。请将用户提供的小说片段转换为剧本格式。"
    "规则：用【场景X 地点】分场；对白前加角色名和冒号；动作/神态用圆括号。"
    "只输出剧本，不要解释。"
)


@app.route("/convert", methods=["POST"])
def convert():
    # ---------- 1. 请求体校验 ----------
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "请求体必须是有效的JSON格式"}), 400

    novel_text = data.get("novel_text")
    if not novel_text or not isinstance(novel_text, str) or not novel_text.strip():
        return jsonify({"error": "缺少必填字段 'novel_text' 或其值为空"}), 400

    # ---------- 2. 构造大模型请求 ----------
    payload = {
        "model": LLM_MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": novel_text.strip()},
        ],
        "temperature": 0.7,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
    }

    # ---------- 3. 调用API并处理响应 ----------
    try:
        resp = requests.post(
            f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()

        result = resp.json()
        content = result["choices"][0]["message"]["content"]

        return jsonify({"script": content})

    except requests.exceptions.HTTPError as e:
        # 大模型API返回了非2xx状态码，尝试提取错误详情
        detail = ""
        try:
            detail = e.response.json().get("error", {}).get("message", "")
        except Exception:
            detail = e.response.text[:500]
        return jsonify({"error": f"大模型API调用失败(HTTP {e.response.status_code}): {detail}"}), 502

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "无法连接到大模型API服务，请检查base_url或网络"}), 502

    except requests.exceptions.Timeout:
        return jsonify({"error": "大模型API请求超时(120s)，请稍后重试"}), 504

    except (KeyError, IndexError, TypeError) as e:
        return jsonify({"error": f"大模型API响应格式异常: {str(e)}"}), 502

    except Exception as e:
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)