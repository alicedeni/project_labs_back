from docx import Document
from langchain_gigachat.chat_models import GigaChat
from langchain_core.prompts import ChatPromptTemplate
import os
import json

class MethodicsAnalyzer:
    def __init__(self):
        self.llm = GigaChat(
            credentials="Y2ZiMDNkNTEtNGZhMC00ODc5LTk5ZDEtNmJmYjNmMzgyNDljOmIyMjllMjVmLTA5MmYtNGU4OC05NWU1LTFkMmE3OWQ2ZTliOQ==",
            verify_ssl_certs=False,
            scope="GIGACHAT_API_PERS",
            temperature=0.5,
            max_tokens=2000
        )
        self.prompt_template = ChatPromptTemplate.from_template(
            """Анализ методички:
            Документ: {document}
            Задача: 
            1. Выявить ключевые требования (структура, критерии, форматы данных)
            2. Сформулировать краткую сводку (3-5 пунктов)
            Ответ в формате JSON:
            {{
                "requirements": ["{requirements}"],
                "summary": ["{summary}"]
            }}"""
        )

    def read_docx(self, file_path):
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])

    def analyze(self, document_path):
        document = self.read_docx(document_path)
        prompt = self.prompt_template.format(
            document=document,
            requirements="[]",
            summary="[]"
        )
        response = self.llm.invoke([{"role": "user", "content": prompt}])
        
        try:
            content = response.content.strip('`json\n ')
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            return {"error": "Некорректный формат ответа"}

